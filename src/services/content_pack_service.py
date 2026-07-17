"""Validate, install, activate, and roll back local season content packs."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from src.__about__ import APP_VERSION
from src.content.repository import ACTIVE_INDEX_NAME, ContentRepository
from src.models.constants import ELEMENTS


PACK_SCHEMA_VERSION = 1
MAX_ARCHIVE_FILES = 512
MAX_ARCHIVE_SIZE = 100 * 1024 * 1024
MAX_SINGLE_FILE_SIZE = 20 * 1024 * 1024
MAX_MANIFEST_SIZE = 256 * 1024
MAX_ROLLBACK_SNAPSHOTS = 5
WINDOWS_REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4)
PACK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class ContentPackError(ValueError):
    """Raised when a content pack is unsafe, invalid, or incompatible."""


@dataclass(frozen=True)
class ContentPackInstallResult:
    season: str
    pack_id: str
    pack_version: int
    activated: bool


@dataclass(frozen=True)
class ContentRollbackResult:
    active_seasons: tuple[str, ...]


class ContentPackService:
    def __init__(
        self,
        repository: ContentRepository,
        content_root: str | Path,
        app_version: str = APP_VERSION,
    ):
        self.repository = repository
        self.content_root = Path(content_root)
        self.app_version = app_version

    def ensure_content_root(self) -> Path:
        self.content_root.mkdir(parents=True, exist_ok=True)
        (self.content_root / "packs").mkdir(parents=True, exist_ok=True)
        return self.content_root

    def install_pack(self, archive_path: str | Path) -> ContentPackInstallResult:
        archive_path = Path(archive_path)
        if not archive_path.is_file():
            raise ContentPackError("资源包文件不存在。")
        self.ensure_content_root()
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.content_root))
        try:
            manifest = self._extract_and_validate(archive_path, staging)
            pack_id = manifest["pack_id"]
            pack_version = manifest["pack_version"]
            season = manifest["season"]
            target = self.content_root / "packs" / f"{pack_id}-v{pack_version}"
            if target.exists():
                installed_manifest = self._read_json(target / "manifest.json")
                if installed_manifest != manifest:
                    raise ContentPackError("本地已存在同 ID、同版本但内容不同的资源包。")
                shutil.rmtree(staging)
            else:
                self._replace_with_retry(
                    staging,
                    target,
                    "Windows 暂时无法写入资源目录。请关闭正在浏览该目录的窗口，或稍后重试。",
                )

            entry = {
                "pack_id": pack_id,
                "pack_version": pack_version,
                "path": PurePosixPath("packs", target.name).as_posix(),
            }
            activated = self._activate(season, entry)
            return ContentPackInstallResult(season, pack_id, pack_version, activated)
        except (RuntimeError, NotImplementedError, EOFError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise ContentPackError("资源包解压失败，压缩文件可能已损坏或使用了不支持的格式。") from exc
        except Exception:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def can_rollback(self) -> bool:
        index = self._load_index()
        stack = index.get("rollback_stack", [])
        return isinstance(stack, list) and bool(stack)

    def rollback(self) -> ContentRollbackResult:
        index = self._load_index()
        stack = index.get("rollback_stack", [])
        if not isinstance(stack, list) or not stack:
            raise ContentPackError("没有可回滚的资源版本。")
        snapshot = stack[-1]
        seasons = snapshot.get("seasons", {}) if isinstance(snapshot, dict) else {}
        if not isinstance(seasons, dict):
            raise ContentPackError("资源回滚记录已损坏。")
        restored = {
            "schema_version": PACK_SCHEMA_VERSION,
            "seasons": copy.deepcopy(seasons),
            "rollback_stack": stack[:-1],
        }
        self._write_index(restored)
        return ContentRollbackResult(tuple(sorted(seasons)))

    def summary(self) -> str:
        return self.repository.summary()

    def _extract_and_validate(self, archive_path: Path, staging: Path) -> dict[str, Any]:
        try:
            archive = zipfile.ZipFile(archive_path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise ContentPackError("无法读取资源包，文件可能已损坏。") from exc

        with archive:
            infos: dict[str, zipfile.ZipInfo] = {}
            total_size = 0
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = self._validate_archive_path(info.filename)
                name = path.as_posix()
                if name in infos:
                    raise ContentPackError(f"资源包包含重复文件：{name}")
                if info.flag_bits & 0x1:
                    raise ContentPackError("不支持加密资源包。")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ContentPackError("资源包不能包含符号链接。")
                if info.file_size > MAX_SINGLE_FILE_SIZE:
                    raise ContentPackError(f"资源文件过大：{name}")
                total_size += info.file_size
                infos[name] = info

            if len(infos) > MAX_ARCHIVE_FILES or total_size > MAX_ARCHIVE_SIZE:
                raise ContentPackError("资源包文件数量或解压后大小超过限制。")
            manifest_info = infos.get("manifest.json")
            if manifest_info is None or manifest_info.file_size > MAX_MANIFEST_SIZE:
                raise ContentPackError("资源包缺少有效的 manifest.json。")
            try:
                manifest = json.loads(archive.read(manifest_info).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContentPackError("manifest.json 不是有效的 UTF-8 JSON。") from exc
            manifest = self._validate_manifest(manifest, set(infos) - {"manifest.json"})

            manifest_path = staging / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as file:
                json.dump(manifest, file, ensure_ascii=False, indent=2)

            for name, expected_hash in manifest["files"].items():
                destination = staging.joinpath(*PurePosixPath(name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.open(infos[name]) as source, open(destination, "wb") as output:
                    while chunk := source.read(1024 * 1024):
                        digest.update(chunk)
                        output.write(chunk)
                if digest.hexdigest().lower() != expected_hash.lower():
                    raise ContentPackError(f"资源文件校验失败：{name}")

        self._validate_season_data(staging / "season.json", manifest["season"])
        self._validate_identity_conflicts(staging / "season.json", manifest["season"])
        for path in (staging / "spirits").glob("*.png") if (staging / "spirits").is_dir() else []:
            self._validate_png(path)
        return manifest

    def _validate_manifest(self, value: Any, payload_names: set[str]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("schema_version") != PACK_SCHEMA_VERSION:
            raise ContentPackError("不支持此资源包格式版本。")
        pack_id = value.get("pack_id")
        pack_version = value.get("pack_version")
        season = value.get("season")
        minimum = value.get("min_app_version", "0.0.0")
        files = value.get("files")
        if not isinstance(pack_id, str) or not PACK_ID_PATTERN.fullmatch(pack_id):
            raise ContentPackError("资源包 pack_id 无效。")
        if isinstance(pack_version, bool) or not isinstance(pack_version, int) or pack_version < 1:
            raise ContentPackError("资源包 pack_version 必须是正整数。")
        if not isinstance(season, str) or not PACK_ID_PATTERN.fullmatch(season):
            raise ContentPackError("资源包赛季 ID 无效。")
        if not isinstance(minimum, str) or self._version_tuple(minimum) is None:
            raise ContentPackError("资源包最低应用版本无效。")
        minimum_version = self._version_tuple(minimum)
        current_version = self._version_tuple(self.app_version)
        if current_version is None:
            raise ContentPackError("当前应用版本号无效，无法判断资源兼容性。")
        if minimum_version > current_version:
            raise ContentPackError(f"此资源包需要 RocoCapture V2 v{minimum} 或更高版本。")
        if not isinstance(files, dict) or "season.json" not in files:
            raise ContentPackError("资源包清单缺少 season.json。")

        normalized_files: dict[str, str] = {}
        for raw_name, digest in files.items():
            path = self._validate_archive_path(raw_name)
            name = path.as_posix()
            if name != "season.json" and not (
                len(path.parts) == 2 and path.parts[0] == "spirits" and path.suffix.lower() == ".png"
            ):
                raise ContentPackError(f"资源包包含不允许的文件：{name}")
            if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                raise ContentPackError(f"资源文件缺少有效 SHA-256：{name}")
            normalized_files[name] = digest.lower()
        if set(normalized_files) != payload_names:
            raise ContentPackError("资源包内容与 manifest.json 文件清单不一致。")

        return {
            "schema_version": PACK_SCHEMA_VERSION,
            "pack_id": pack_id,
            "pack_version": pack_version,
            "season": season,
            "min_app_version": minimum,
            "files": normalized_files,
        }

    @staticmethod
    def _validate_archive_path(value: object) -> PurePosixPath:
        if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
            raise ContentPackError("资源包包含无效文件路径。")
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ContentPackError("资源包包含不安全文件路径。")
        return path

    @staticmethod
    def _validate_season_data(path: Path, expected_season: str) -> None:
        data = ContentPackService._read_json(path)
        if not isinstance(data, dict) or data.get("season") != expected_season:
            raise ContentPackError("season.json 的赛季 ID 与资源包清单不一致。")
        spirits = data.get("spirits")
        if not isinstance(spirits, list) or len(spirits) > 1000:
            raise ContentPackError("season.json 的精灵列表无效。")
        identities: set[tuple[int, str]] = set()
        for spirit in spirits:
            if not isinstance(spirit, dict):
                raise ContentPackError("season.json 包含无效精灵数据。")
            number = spirit.get("no")
            name = spirit.get("name")
            elements = spirit.get("elements", [])
            if isinstance(number, bool) or not isinstance(number, int) or number < 1:
                raise ContentPackError("精灵编号必须是正整数。")
            if not isinstance(name, str) or not name.strip() or len(name) > 80:
                raise ContentPackError("精灵名称无效。")
            if not isinstance(elements, list) or len(elements) > 4 or any(
                not isinstance(element, str) or not element.strip() or len(element) > 16
                for element in elements
            ):
                raise ContentPackError(f"精灵「{name}」的属性数据无效。")
            unsupported = [element for element in elements if element not in ELEMENTS]
            if unsupported:
                raise ContentPackError(f"精灵「{name}」包含当前版本不支持的属性：{'、'.join(unsupported)}")
            identity = (number, name.strip())
            if identity in identities:
                raise ContentPackError(f"season.json 包含重复精灵：No.{number:03d} {name}")
            identities.add(identity)

    def _validate_identity_conflicts(self, season_path: Path, replacing_season: str) -> None:
        candidate = self._read_json(season_path)
        existing_by_number: dict[int, str] = {}
        for season in self.repository.load_seasons():
            if str(season.get("season", "")) == replacing_season:
                continue
            for spirit in season.get("spirits", []):
                existing_by_number[int(spirit["no"])] = str(spirit["name"])
        for spirit in candidate.get("spirits", []):
            number = int(spirit["no"])
            name = str(spirit["name"])
            existing_name = existing_by_number.get(number)
            if existing_name is not None and existing_name != name:
                raise ContentPackError(
                    f"精灵编号 No.{number:03d} 已被「{existing_name}」使用，不能再用于「{name}」。"
                )

    @staticmethod
    def _validate_png(path: Path) -> None:
        try:
            with open(path, "rb") as file:
                header = file.read(24)
        except OSError as exc:
            raise ContentPackError(f"无法读取图片：{path.name}") from exc
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise ContentPackError(f"资源图片不是有效 PNG：{path.name}")
        width, height = struct.unpack(">II", header[16:24])
        if not 16 <= width <= 4096 or not 16 <= height <= 4096:
            raise ContentPackError(f"资源图片尺寸超出限制：{path.name}")

    def _activate(self, season: str, entry: dict[str, Any]) -> bool:
        index = self._load_index()
        seasons = index.get("seasons", {})
        if not isinstance(seasons, dict):
            seasons = {}
        if seasons.get(season) == entry:
            return False
        stack = index.get("rollback_stack", [])
        if not isinstance(stack, list):
            stack = []
        stack = (stack + [{"seasons": copy.deepcopy(seasons)}])[-MAX_ROLLBACK_SNAPSHOTS:]
        updated_seasons = copy.deepcopy(seasons)
        updated_seasons[season] = entry
        self._write_index({
            "schema_version": PACK_SCHEMA_VERSION,
            "seasons": updated_seasons,
            "rollback_stack": stack,
        })
        return True

    def _load_index(self) -> dict[str, Any]:
        index = self.repository.read_active_index()
        if not isinstance(index, dict):
            return {"schema_version": PACK_SCHEMA_VERSION, "seasons": {}, "rollback_stack": []}
        return index

    def _write_index(self, index: dict[str, Any]) -> None:
        self.ensure_content_root()
        target = self.content_root / ACTIVE_INDEX_NAME
        temporary = self.content_root / f".{ACTIVE_INDEX_NAME}.{uuid.uuid4().hex}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as file:
                json.dump(index, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            self._replace_with_retry(
                temporary,
                target,
                "Windows 暂时无法更新资源配置。请关闭正在浏览该目录的窗口，或稍后重试。",
            )
        finally:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

    @staticmethod
    def _replace_with_retry(source: Path, target: Path, error_message: str) -> None:
        last_error: PermissionError | None = None
        for delay in (*WINDOWS_REPLACE_RETRY_DELAYS, None):
            try:
                os.replace(source, target)
                return
            except PermissionError as exc:
                last_error = exc
                if delay is None:
                    break
                time.sleep(delay)
        raise ContentPackError(error_message) from last_error

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _version_tuple(version: str) -> tuple[int, int, int] | None:
        normalized = version.strip().lower().lstrip("v")
        normalized = re.split(r"[-+]", normalized, maxsplit=1)[0]
        parts = normalized.split(".")
        if not 1 <= len(parts) <= 3 or any(not part.isdigit() for part in parts):
            return None
        numbers = [int(part) for part in parts]
        numbers.extend([0] * (3 - len(numbers)))
        return tuple(numbers)

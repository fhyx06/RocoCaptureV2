"""Resolve built-in game content plus optional local season-pack overrides."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any


BUILTIN_CONTENT_ROOT = Path(__file__).resolve().parents[1] / "assets"
ACTIVE_INDEX_NAME = "active.json"


def _season_sort_key(season_data: dict) -> tuple[int, str]:
    season_id = str(season_data.get("season", ""))
    match = re.search(r"\d+", season_id)
    return (int(match.group()) if match else -1, season_id)


@dataclass(frozen=True)
class ActiveContentPack:
    season: str
    pack_id: str
    pack_version: int
    path: Path

    @property
    def display_version(self) -> str:
        return f"{self.season} v{self.pack_version}"


class ContentRepository:
    """Layer local active packs over immutable content bundled with the app."""

    def __init__(
        self,
        builtin_root: str | Path | None = None,
        external_root: str | Path | None = None,
    ):
        self.builtin_root = Path(builtin_root or BUILTIN_CONTENT_ROOT)
        self._external_root = Path(external_root) if external_root else None
        self._lock = RLock()
        self._season_cache: list[dict] | None = None
        self._spirit_file_cache: tuple[tuple[str, Path], ...] | None = None

    @property
    def external_root(self) -> Path | None:
        return self._external_root

    def configure_external_root(self, root: str | Path | None) -> None:
        with self._lock:
            self._external_root = Path(root) if root else None
            self.invalidate()

    def invalidate(self) -> None:
        with self._lock:
            self._season_cache = None
            self._spirit_file_cache = None

    def load_seasons(self) -> list[dict]:
        with self._lock:
            if self._season_cache is not None:
                return copy.deepcopy(self._season_cache)

            seasons: dict[str, dict] = {}
            builtin_dir = self.builtin_root / "seasons"
            for path in sorted(builtin_dir.glob("*.json")) if builtin_dir.is_dir() else []:
                data = self._read_json(path)
                season_id = str(data.get("season", "")) if isinstance(data, dict) else ""
                if season_id and isinstance(data.get("spirits"), list):
                    seasons[season_id] = data

            for pack in self.active_packs():
                data = self._read_json(pack.path / "season.json")
                if (
                    isinstance(data, dict)
                    and str(data.get("season", "")) == pack.season
                    and isinstance(data.get("spirits"), list)
                ):
                    seasons[pack.season] = data

            self._season_cache = sorted(seasons.values(), key=_season_sort_key)
            return copy.deepcopy(self._season_cache)

    def spirit_files(self) -> tuple[tuple[str, Path], ...]:
        """Return (season, PNG path) pairs with local overrides ordered last."""
        with self._lock:
            if self._spirit_file_cache is not None:
                return self._spirit_file_cache

            files: list[tuple[str, Path]] = []
            builtin_dir = self.builtin_root / "spirits"
            if builtin_dir.is_dir():
                for path in sorted(builtin_dir.rglob("*.png")):
                    season = path.parent.name if path.parent != builtin_dir else ""
                    files.append((season, path))
            for pack in self.active_packs():
                spirit_dir = pack.path / "spirits"
                try:
                    pack_files = sorted(spirit_dir.glob("*.png")) if spirit_dir.is_dir() else []
                except OSError:
                    # An external pack can become temporarily unavailable because of
                    # permissions, antivirus scanning, or a removable/network drive.
                    # Keep built-in content usable instead of crashing the UI.
                    continue
                files.extend((pack.season, path) for path in pack_files)
            self._spirit_file_cache = tuple(files)
            return self._spirit_file_cache

    def active_packs(self) -> tuple[ActiveContentPack, ...]:
        index = self.read_active_index()
        seasons = index.get("seasons", {})
        if not isinstance(seasons, dict):
            return ()
        packs: list[ActiveContentPack] = []
        for season, raw in seasons.items():
            if not isinstance(season, str) or not season or not isinstance(raw, dict):
                continue
            path = self._resolve_external_path(raw.get("path"))
            pack_id = raw.get("pack_id")
            pack_version = raw.get("pack_version")
            try:
                path_is_dir = path.is_dir() if path is not None else False
            except OSError:
                path_is_dir = False
            if (
                path is None
                or not path_is_dir
                or not isinstance(pack_id, str)
                or not isinstance(pack_version, int)
                or pack_version < 1
            ):
                continue
            packs.append(ActiveContentPack(season, pack_id, pack_version, path))
        return tuple(sorted(packs, key=lambda item: _season_sort_key({"season": item.season})))

    def read_active_index(self) -> dict[str, Any]:
        root = self._external_root
        if root is None:
            return {"schema_version": 1, "seasons": {}, "rollback_stack": []}
        data = self._read_json(root / ACTIVE_INDEX_NAME)
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            return {"schema_version": 1, "seasons": {}, "rollback_stack": []}
        return data

    def summary(self) -> str:
        builtin_ids = []
        builtin_dir = self.builtin_root / "seasons"
        for path in sorted(builtin_dir.glob("*.json")) if builtin_dir.is_dir() else []:
            data = self._read_json(path)
            if isinstance(data, dict) and data.get("season"):
                builtin_ids.append(str(data["season"]))
        builtin_text = "、".join(builtin_ids) if builtin_ids else "无"
        packs = self.active_packs()
        if not packs:
            return f"内置资源：{builtin_text} · 尚未安装本地资源包"
        local_text = "、".join(pack.display_version for pack in packs)
        return f"内置资源：{builtin_text} · 本地启用：{local_text}"

    def _resolve_external_path(self, value: object) -> Path | None:
        root = self._external_root
        if root is None or not isinstance(value, str) or "\\" in value:
            return None
        relative = PurePosixPath(value)
        if relative.is_absolute() or not relative.parts or relative.parts[0] != "packs":
            return None
        if any(part in {"", ".", ".."} for part in relative.parts):
            return None
        candidate = (root / Path(*relative.parts)).resolve()
        resolved_root = root.resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            return None
        return candidate

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None


_DEFAULT_REPOSITORY = ContentRepository()


def get_content_repository() -> ContentRepository:
    return _DEFAULT_REPOSITORY


def configure_content_root(root: str | Path | None) -> ContentRepository:
    _DEFAULT_REPOSITORY.configure_external_root(root)
    return _DEFAULT_REPOSITORY

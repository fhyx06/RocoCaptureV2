"""Build a validated season content ZIP for manual import into the app."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.__about__ import APP_VERSION
from src.services.content_pack_service import ContentPackService, PACK_ID_PATTERN


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_content_pack(
    season_file: Path,
    spirits_dir: Path,
    output: Path,
    pack_version: int,
    pack_id: str | None = None,
    min_app_version: str = APP_VERSION,
) -> Path:
    try:
        season_data = json.loads(season_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("赛季文件不是有效的 UTF-8 JSON。") from exc
    season = str(season_data.get("season", "")) if isinstance(season_data, dict) else ""
    resolved_pack_id = pack_id or season
    if not season or not PACK_ID_PATTERN.fullmatch(season):
        raise ValueError("赛季 ID 无效。")
    if not PACK_ID_PATTERN.fullmatch(resolved_pack_id):
        raise ValueError("资源包 ID 无效。")
    if pack_version < 1:
        raise ValueError("资源包版本必须是正整数。")
    if ContentPackService._version_tuple(min_app_version) is None:
        raise ValueError("最低应用版本无效。")

    ContentPackService._validate_season_data(season_file, season)
    payloads: dict[str, bytes] = {"season.json": season_file.read_bytes()}
    if spirits_dir.is_dir():
        for path in sorted(spirits_dir.glob("*.png")):
            ContentPackService._validate_png(path)
            payloads[f"spirits/{path.name}"] = path.read_bytes()

    manifest = {
        "schema_version": 1,
        "pack_id": resolved_pack_id,
        "pack_version": pack_version,
        "season": season,
        "min_app_version": min_app_version,
        "files": {name: _sha256(data) for name, data in payloads.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        for name, data in payloads.items():
            archive.writestr(name, data)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 RocoCapture V2 赛季资源包")
    parser.add_argument("--season-file", type=Path, required=True, help="赛季 JSON 文件")
    parser.add_argument("--spirits-dir", type=Path, required=True, help="精灵 PNG 目录")
    parser.add_argument("--version", type=int, required=True, help="资源包版本号")
    parser.add_argument("--output", type=Path, required=True, help="输出 ZIP 路径")
    parser.add_argument("--pack-id", help="资源包 ID，默认使用赛季 ID")
    parser.add_argument("--min-app-version", default=APP_VERSION, help="最低应用版本")
    args = parser.parse_args()
    result = build_content_pack(
        args.season_file,
        args.spirits_dir,
        args.output,
        args.version,
        args.pack_id,
        args.min_app_version,
    )
    print(result)


if __name__ == "__main__":
    main()

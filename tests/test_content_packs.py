from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.content.repository import BUILTIN_CONTENT_ROOT, ContentRepository
from src.services.content_pack_service import ContentPackError, ContentPackService
from src.services.save_service import SaveService
from scripts.build_content_pack import build_content_pack


class ContentPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "content"
        self.repository = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        self.service = ContentPackService(self.repository, self.root, "0.3.2")
        self.png_data = next((BUILTIN_CONTENT_ROOT / "spirits").rglob("*.png")).read_bytes()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_pack(
        self,
        *,
        version: int = 1,
        spirit_name: str = "测试精灵",
        season: str = "S3",
        number: int = 999,
        min_app_version: str = "0.3.2",
        corrupt_hash: bool = False,
        traversal: bool = False,
    ) -> Path:
        season_data = {
            "season": season,
            "label": f"{season} 测试赛季",
            "spirits": [{"no": number, "name": spirit_name, "elements": ["火"]}],
        }
        payloads = {
            "season.json": json.dumps(season_data, ensure_ascii=False).encode("utf-8"),
            f"spirits/NO.{number:03d} {spirit_name}.png": self.png_data,
        }
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
        if corrupt_hash:
            hashes["season.json"] = "0" * 64
        manifest = {
            "schema_version": 1,
            "pack_id": season,
            "pack_version": version,
            "season": season,
            "min_app_version": min_app_version,
            "files": hashes,
        }
        archive_path = Path(self.temp_dir.name) / f"{season}-v{version}-{spirit_name}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
            for name, data in payloads.items():
                archive.writestr(name, data)
            if traversal:
                archive.writestr("../escape.png", self.png_data)
        return archive_path

    def test_valid_pack_adds_season_and_spirit_image_after_restart(self) -> None:
        result = self.service.install_pack(self._build_pack())
        self.assertTrue(result.activated)
        self.assertEqual(result.season, "S3")
        fresh = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        seasons = {item["season"]: item for item in fresh.load_seasons()}
        self.assertIn("S3", seasons)
        self.assertEqual(seasons["S3"]["spirits"][0]["name"], "测试精灵")
        self.assertTrue(any(season == "S3" for season, _path in fresh.spirit_files()))
        self.assertIn("S3 v1", fresh.summary())

    def test_old_save_is_supplemented_without_losing_existing_counts(self) -> None:
        saves = SaveService(Path(self.temp_dir.name) / "saves")
        slot = saves.create_save("old")
        old_name = next(iter(slot.family_pool))
        slot.family_pool[old_name] = 12
        saves.save_current()

        self.service.install_pack(self._build_pack())
        fresh = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        with patch("src.services.save_service.load_seasons", fresh.load_seasons):
            loaded = saves.load_save("old")
        self.assertEqual(loaded.family_pool[old_name], 12)
        self.assertIn("No.999 测试精灵", loaded.family_pool)
        self.assertEqual(loaded.family_pool["No.999 测试精灵"], 0)

    def test_newer_pack_can_be_rolled_back_to_previous_version(self) -> None:
        self.service.install_pack(self._build_pack(version=1, spirit_name="旧名称"))
        self.service.install_pack(self._build_pack(version=2, spirit_name="新名称"))
        current = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        current_s3 = next(item for item in current.load_seasons() if item["season"] == "S3")
        self.assertEqual(current_s3["spirits"][0]["name"], "新名称")
        self.assertTrue(self.service.can_rollback())

        result = self.service.rollback()
        self.assertEqual(result.active_seasons, ("S3",))
        restored = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        restored_s3 = next(item for item in restored.load_seasons() if item["season"] == "S3")
        self.assertEqual(restored_s3["spirits"][0]["name"], "旧名称")

    def test_corrupt_hash_does_not_activate_pack(self) -> None:
        with self.assertRaisesRegex(ContentPackError, "校验失败"):
            self.service.install_pack(self._build_pack(corrupt_hash=True))
        self.assertEqual(self.repository.active_packs(), ())

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContentPackError, "不安全文件路径"):
            self.service.install_pack(self._build_pack(traversal=True))
        self.assertFalse((Path(self.temp_dir.name) / "escape.png").exists())

    def test_incompatible_minimum_app_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContentPackError, "需要 RocoCapture"):
            self.service.install_pack(self._build_pack(min_app_version="9.0.0"))

    def test_name_correction_keeps_existing_pity_by_spirit_number(self) -> None:
        saves = SaveService(Path(self.temp_dir.name) / "rename-saves")
        slot = saves.create_save("old")
        slot.family_pool["No.041 奇丽草"] = 37
        saves.save_current()
        self.service.install_pack(
            self._build_pack(season="S1", number=41, spirit_name="奇丽草新名称")
        )
        fresh = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        with patch("src.services.save_service.load_seasons", fresh.load_seasons):
            loaded = saves.load_save("old")
        self.assertNotIn("No.041 奇丽草", loaded.family_pool)
        self.assertEqual(loaded.family_pool["No.041 奇丽草新名称"], 37)

    def test_conflicting_global_spirit_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContentPackError, "已被"):
            self.service.install_pack(
                self._build_pack(season="S3", number=41, spirit_name="另一个精灵")
            )

    def test_builder_creates_an_importable_pack(self) -> None:
        output = Path(self.temp_dir.name) / "S1-v1.zip"
        build_content_pack(
            BUILTIN_CONTENT_ROOT / "seasons" / "S1.json",
            BUILTIN_CONTENT_ROOT / "spirits" / "S1",
            output,
            1,
        )
        result = self.service.install_pack(output)
        self.assertEqual(result.season, "S1")
        self.assertTrue(result.activated)

    def test_install_retries_a_transient_windows_directory_lock(self) -> None:
        real_replace = os.replace
        blocked_once = False

        def transient_replace(source: str | Path, target: str | Path) -> None:
            nonlocal blocked_once
            if Path(target).name == "S3-v1" and not blocked_once:
                blocked_once = True
                raise PermissionError(5, "Access is denied")
            real_replace(source, target)

        with (
            patch("src.services.content_pack_service.os.replace", side_effect=transient_replace),
            patch("src.services.content_pack_service.time.sleep") as sleep,
        ):
            result = self.service.install_pack(self._build_pack())

        self.assertTrue(result.activated)
        sleep.assert_called_once_with(0.05)

    def test_persistent_windows_directory_lock_has_a_clear_error(self) -> None:
        with (
            patch(
                "src.services.content_pack_service.os.replace",
                side_effect=PermissionError(5, "Access is denied"),
            ),
            patch("src.services.content_pack_service.time.sleep"),
        ):
            with self.assertRaisesRegex(ContentPackError, "Windows 暂时无法写入资源目录"):
                self.service.install_pack(self._build_pack())

    def test_inaccessible_spirit_directory_does_not_crash_resource_lookup(self) -> None:
        self.service.install_pack(self._build_pack())
        fresh = ContentRepository(BUILTIN_CONTENT_ROOT, self.root)
        denied = (self.root / "packs" / "S3-v1" / "spirits").resolve()
        real_is_dir = Path.is_dir

        def selective_is_dir(path: Path) -> bool:
            if path.resolve() == denied:
                raise PermissionError(5, "Access is denied")
            return real_is_dir(path)

        with patch.object(Path, "is_dir", selective_is_dir):
            files = fresh.spirit_files()

        self.assertTrue(files)
        self.assertFalse(any(season == "S3" for season, _path in files))


if __name__ == "__main__":
    unittest.main()

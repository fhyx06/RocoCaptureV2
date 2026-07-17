"""Qt 应用入口。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.__about__ import APP_NAME, APP_VERSION
from src.content.repository import configure_content_root
from src.models.constants import SAVES_DIR
from src.services.content_pack_service import ContentPackService
from src.services.save_service import SaveService
from src.services.settings_service import SETTINGS_FILE_NAME, SettingsService
from src.qt_ui_v2.main_window import QtMainWindowV2
from src.qt_ui_v2.theme import apply_theme, configure_font


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    configure_font(app)

    app_dir = Path(sys.argv[0]).resolve().parent
    saves_dir = app_dir / SAVES_DIR
    content_root = app_dir / "data" / "content"
    content_repository = configure_content_root(content_root)
    content_pack_service = ContentPackService(content_repository, content_root)
    settings_service = SettingsService(os.path.join(saves_dir, SETTINGS_FILE_NAME))
    apply_theme(app, settings_service.theme)

    save_service = SaveService(saves_dir)
    if not save_service.list_saves():
        save_service.create_save("主账号")

    window = QtMainWindowV2(save_service, settings_service, content_pack_service)
    window.show()
    sys.exit(app.exec())

"""Qt 应用入口。"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.__about__ import APP_NAME, APP_VERSION
from src.models.constants import SAVES_DIR
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

    saves_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), SAVES_DIR)
    settings_service = SettingsService(os.path.join(saves_dir, SETTINGS_FILE_NAME))
    apply_theme(app, settings_service.theme)

    save_service = SaveService(saves_dir)
    if not save_service.list_saves():
        save_service.create_save("主账号")

    window = QtMainWindowV2(save_service, settings_service)
    window.show()
    sys.exit(app.exec())

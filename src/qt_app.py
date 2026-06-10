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
from src.qt_ui.main_window import QtMainWindow
from src.qt_ui.theme import build_stylesheet


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    saves_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), SAVES_DIR)
    settings_service = SettingsService(os.path.join(saves_dir, SETTINGS_FILE_NAME))
    app.setStyleSheet(build_stylesheet(settings_service.theme))

    save_service = SaveService(saves_dir)
    if not save_service.list_saves():
        save_service.create_save("主账号")

    window = QtMainWindow(save_service, settings_service)
    window.show()
    sys.exit(app.exec())

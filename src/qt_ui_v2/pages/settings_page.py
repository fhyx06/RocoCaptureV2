from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.__about__ import APP_DISPLAY_NAME, APP_VERSION


class SettingsPage(QWidget):
    theme_toggle_requested = Signal()
    update_check_requested = Signal()
    github_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("设置")
        title.setObjectName("pageTitle")
        subtitle = QLabel("调整外观并查看应用版本与更新信息。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        appearance = QFrame()
        appearance.setObjectName("detailCard")
        appearance_layout = QHBoxLayout(appearance)
        appearance_layout.setContentsMargins(20, 18, 20, 18)
        text = QVBoxLayout()
        heading = QLabel("外观")
        heading.setObjectName("detailTitle")
        hint = QLabel("在深色和浅色主题之间切换。")
        hint.setObjectName("detailMeta")
        text.addWidget(heading)
        text.addWidget(hint)
        appearance_layout.addLayout(text, 1)
        self.theme_btn = QPushButton("切换主题")
        self.theme_btn.clicked.connect(self.theme_toggle_requested.emit)
        appearance_layout.addWidget(self.theme_btn)
        layout.addWidget(appearance)

        about = QFrame()
        about.setObjectName("detailCard")
        about_layout = QHBoxLayout(about)
        about_layout.setContentsMargins(20, 18, 20, 18)
        about_text = QVBoxLayout()
        heading = QLabel(APP_DISPLAY_NAME)
        heading.setObjectName("detailTitle")
        self.update_status = QLabel(f"当前版本 v{APP_VERSION}")
        self.update_status.setObjectName("detailMeta")
        about_text.addWidget(heading)
        about_text.addWidget(self.update_status)
        about_layout.addLayout(about_text, 1)
        github = QPushButton("GitHub 项目")
        check = QPushButton("检查更新")
        check.setProperty("role", "primary")
        github.clicked.connect(self.github_requested.emit)
        check.clicked.connect(self.update_check_requested.emit)
        about_layout.addWidget(github)
        about_layout.addWidget(check)
        self.update_btn = check
        layout.addWidget(about)
        layout.addStretch()

    def set_theme_name(self, theme_name: str) -> None:
        self.theme_btn.setText("切换到浅色主题" if theme_name == "dark" else "切换到深色主题")

    def set_update_checking(self, checking: bool) -> None:
        self.update_btn.setEnabled(not checking)
        self.update_btn.setText("检查中…" if checking else "检查更新")

"""Semantic theme and typography for the V2 interface."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from src.services.settings_service import THEME_DARK, THEME_LIGHT


PALETTES = {
    THEME_DARK: {
        "window": "#11141a",
        "sidebar": "#151922",
        "surface": "#1b202b",
        "surface_alt": "#222936",
        "hover": "#282f3e",
        "border": "#30394a",
        "text": "#edf2f8",
        "muted": "#96a2b4",
        "subtle": "#6f7b8d",
        "accent": "#6f9df7",
        "accent_hover": "#82adff",
        "accent_soft": "#22304d",
        "warning": "#e0a14a",
        "warning_soft": "#3a2d1c",
        "critical": "#ed6a78",
        "critical_soft": "#42242c",
        "success": "#57c7a5",
    },
    THEME_LIGHT: {
        "window": "#f3f5f8",
        "sidebar": "#e9edf3",
        "surface": "#ffffff",
        "surface_alt": "#f7f9fc",
        "hover": "#edf1f7",
        "border": "#d8dee8",
        "text": "#202938",
        "muted": "#68758a",
        "subtle": "#8b96a7",
        "accent": "#3975dc",
        "accent_hover": "#2d65c2",
        "accent_soft": "#e5eeff",
        "warning": "#b87318",
        "warning_soft": "#fff2dc",
        "critical": "#c8495a",
        "critical_soft": "#ffe9ed",
        "success": "#178c6d",
    },
}


def configure_font(app: QApplication) -> None:
    """Use a point-sized Windows UI font with explicit Chinese fallbacks."""
    available = set(QFontDatabase.families())
    preferred = [
        family
        for family in (
            "Segoe UI Variable Text",
            "Microsoft YaHei UI",
            "Segoe UI",
            "Microsoft YaHei",
        )
        if family in available
    ]
    font = QFont()
    if preferred:
        font.setFamilies(preferred)
    font.setPointSize(10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)


def apply_theme(app: QApplication, theme_name: str) -> None:
    name = theme_name if theme_name in PALETTES else THEME_DARK
    colors = PALETTES[name]
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surface_alt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface_alt"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent_soft"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["subtle"]))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(name))


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def build_stylesheet(theme_name: str) -> str:
    c = PALETTES.get(theme_name, PALETTES[THEME_DARK])
    return f"""
QMainWindow, QDialog, QWidget#appRoot {{
    background: {c['window']};
    color: {c['text']};
}}
QWidget {{
    color: {c['text']};
}}
QWidget#topBar, QWidget#sidebar {{
    background: {c['sidebar']};
}}
QWidget#pageHost {{
    background: {c['window']};
}}
QFrame#card, QWidget#card, QFrame#detailCard, QFrame#filterBar {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
QFrame#activityDrawer {{
    background: {c['sidebar']};
    border-left: 1px solid {c['border']};
}}
QLabel#brand {{
    color: {c['text']};
    font-size: 13pt;
    font-weight: 600;
}}
QLabel#version {{ color: {c['muted']}; font-size: 9pt; }}
QLabel#pageTitle {{ color: {c['text']}; font-size: 17pt; font-weight: 600; }}
QLabel#pageSubtitle, QLabel#muted, QLabel#detailMeta {{ color: {c['muted']}; }}
QLabel#detailTitle {{ color: {c['text']}; font-size: 14pt; font-weight: 600; }}
QLabel#countValue {{ color: {c['text']}; font-size: 36pt; font-weight: 600; }}
QLabel#countValue[state="warn"] {{ color: {c['warning']}; }}
QLabel#countValue[state="critical"] {{ color: {c['critical']}; }}
QLabel#countCaption {{ color: {c['muted']}; font-size: 9pt; }}
QLabel#badge {{
    background: {c['surface_alt']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['muted']};
    padding: 3px 8px;
}}
QPushButton, QToolButton {{
    background: {c['surface_alt']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['text']};
    min-height: 34px;
    padding: 0 12px;
}}
QPushButton:hover, QToolButton:hover {{
    background: {c['hover']};
    border-color: {c['accent']};
}}
QPushButton:pressed, QToolButton:pressed {{ background: {c['accent_soft']}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {c['subtle']}; border-color: {c['border']}; }}
QPushButton[role="primary"] {{
    background: {c['accent']};
    border-color: {c['accent']};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background: {c['accent_hover']}; }}
QPushButton[role="shiny"] {{
    background: {c['warning_soft']};
    border-color: {c['warning']};
    color: {c['warning']};
    font-weight: 600;
}}
QPushButton[role="danger"] {{ color: {c['critical']}; }}
QPushButton#navButton {{
    background: transparent;
    border: none;
    border-radius: 9px;
    color: {c['muted']};
    min-height: 44px;
    padding: 0 14px;
    text-align: left;
}}
QPushButton#navButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#navButton:checked {{
    background: {c['accent_soft']};
    color: {c['accent']};
    font-weight: 600;
}}
QPushButton#randomQuick {{
    background: {c['accent_soft']};
    color: {c['accent']};
    border-color: transparent;
}}
QPushButton#elementCard {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    min-height: 62px;
    text-align: left;
    padding: 8px 12px;
}}
QPushButton#elementCard:hover, QPushButton#elementCard:checked {{ border-color: {c['accent']}; background: {c['accent_soft']}; }}
QPushButton#elementCard[state="warn"] {{ border-color: {c['warning']}; color: {c['warning']}; }}
QPushButton#elementCard[state="critical"] {{ border-color: {c['critical']}; color: {c['critical']}; }}
QLineEdit, QComboBox, QSpinBox {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['text']};
    min-height: 34px;
    padding: 0 10px;
    selection-background-color: {c['accent_soft']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {c['accent']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {c['surface']};
    border: 1px solid {c['border']};
    color: {c['text']};
    selection-background-color: {c['accent_soft']};
}}
QTabBar::tab {{
    background: transparent;
    color: {c['muted']};
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 64px;
    min-height: 34px;
    padding: 0 8px;
}}
QTabBar::tab:hover {{ color: {c['text']}; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; font-weight: 600; }}
QListView, QTableView {{
    background: {c['surface']};
    alternate-background-color: {c['surface_alt']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    outline: none;
    selection-background-color: {c['accent_soft']};
    selection-color: {c['text']};
}}
QTableView {{ gridline-color: {c['border']}; }}
QHeaderView::section {{
    background: {c['surface_alt']};
    color: {c['muted']};
    border: none;
    border-bottom: 1px solid {c['border']};
    padding: 8px;
    font-weight: 600;
}}
QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 6px; }}
QMenu::item {{ border-radius: 6px; padding: 7px 26px 7px 10px; }}
QMenu::item:selected {{ background: {c['accent_soft']}; color: {c['accent']}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 3px; min-width: 28px; }}
QSplitter::handle {{ background: transparent; }}
QToolTip {{ background: {c['surface_alt']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 5px; }}
"""

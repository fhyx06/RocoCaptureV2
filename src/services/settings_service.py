"""应用级配置读写服务。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, SAVES_DIR


SETTINGS_FILE_NAME = "settings.json"
THEME_DARK = "dark"
THEME_LIGHT = "light"
SUPPORTED_THEMES = {THEME_DARK, THEME_LIGHT}
LOG_COLOR_OTHER = "other"

DEFAULT_LOG_COLORS = {
    THEME_DARK: {
        POOL_FAMILY: {"accent": "#f3b34b", "text": "#f1d39a", "bg": "#2b251b"},
        POOL_RANDOM: {"accent": "#78a9ff", "text": "#b9d3ff", "bg": "#1f2736"},
        POOL_ELEMENT: {"accent": "#6fb8a6", "text": "#a8d9ce", "bg": "#1d2b2a"},
        LOG_COLOR_OTHER: {"accent": "#8e98a8", "text": "#b8c0cc", "bg": "#222630"},
    },
    THEME_LIGHT: {
        POOL_FAMILY: {"accent": "#b7791f", "text": "#7c4a03", "bg": "#fff6df"},
        POOL_RANDOM: {"accent": "#2563eb", "text": "#1d4ed8", "bg": "#eaf1ff"},
        POOL_ELEMENT: {"accent": "#0f9f7a", "text": "#047857", "bg": "#e6f7f2"},
        LOG_COLOR_OTHER: {"accent": "#64748b", "text": "#475569", "bg": "#eef2f7"},
    },
}

DEFAULT_SETTINGS = {
    "theme": THEME_DARK,
    "log_colors": DEFAULT_LOG_COLORS,
}


class SettingsService:
    """管理 portable 程序的应用级配置。"""

    def __init__(self, settings_path: str | Path | None = None):
        self.settings_path = Path(settings_path or Path(SAVES_DIR) / SETTINGS_FILE_NAME)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load()

    @property
    def theme(self) -> str:
        theme = str(self._settings.get("theme", THEME_DARK))
        return theme if theme in SUPPORTED_THEMES else THEME_DARK

    def set_theme(self, theme: str) -> None:
        if theme not in SUPPORTED_THEMES:
            raise ValueError(f"Unsupported theme: {theme}")
        self._settings["theme"] = theme
        self.save()

    def toggle_theme(self) -> str:
        theme = THEME_LIGHT if self.theme == THEME_DARK else THEME_DARK
        self.set_theme(theme)
        return theme

    def log_colors(self, theme: str | None = None) -> dict[str, dict[str, str]]:
        theme_name = theme if theme in SUPPORTED_THEMES else self.theme
        all_colors = self._settings.get("log_colors", {})
        if self._is_single_log_palette(all_colors):
            return self._merge_log_palette(DEFAULT_LOG_COLORS[theme_name], all_colors)
        theme_colors = all_colors.get(theme_name, {}) if isinstance(all_colors, dict) else {}
        return self._merge_log_palette(DEFAULT_LOG_COLORS[theme_name], theme_colors)

    def save(self) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, ensure_ascii=False, indent=2)

    def _load(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            settings = copy.deepcopy(DEFAULT_SETTINGS)
            self._write_settings(settings)
            return settings
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return copy.deepcopy(DEFAULT_SETTINGS)
        if not isinstance(data, dict):
            return copy.deepcopy(DEFAULT_SETTINGS)
        return self._merge_settings(data)

    def _merge_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        theme = str(data.get("theme", THEME_DARK))
        settings["theme"] = theme if theme in SUPPORTED_THEMES else THEME_DARK

        log_colors = data.get("log_colors", {})
        if self._is_single_log_palette(log_colors):
            settings["log_colors"] = {
                THEME_DARK: self._merge_log_palette(DEFAULT_LOG_COLORS[THEME_DARK], log_colors),
                THEME_LIGHT: copy.deepcopy(DEFAULT_LOG_COLORS[THEME_LIGHT]),
            }
        elif isinstance(log_colors, dict):
            settings["log_colors"] = {
                theme_name: self._merge_log_palette(
                    DEFAULT_LOG_COLORS[theme_name],
                    log_colors.get(theme_name, {}),
                )
                for theme_name in (THEME_DARK, THEME_LIGHT)
            }
        return settings

    @staticmethod
    def _merge_log_palette(
        default: dict[str, dict[str, str]],
        overrides: Any,
    ) -> dict[str, dict[str, str]]:
        palette = copy.deepcopy(default)
        if not isinstance(overrides, dict):
            return palette
        for pool_type, colors in overrides.items():
            if pool_type not in palette or not isinstance(colors, dict):
                continue
            for key in ("accent", "text", "bg"):
                value = colors.get(key)
                if isinstance(value, str) and value.strip():
                    palette[pool_type][key] = value.strip()
        return palette

    @staticmethod
    def _is_single_log_palette(value: Any) -> bool:
        return (
            isinstance(value, dict)
            and any(isinstance(colors, dict) and "accent" in colors for colors in value.values())
        )

    def _write_settings(self, settings: dict[str, Any]) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

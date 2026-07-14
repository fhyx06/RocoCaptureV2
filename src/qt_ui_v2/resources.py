"""Cached application resources used by the V2 interface."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QIcon


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
V2_ICONS_DIR = ICONS_DIR / "v2"
SPIRITS_DIR = ASSETS_DIR / "spirits"


def spirit_display(spirit: dict) -> str:
    return f"No.{int(spirit['no']):03d} {spirit['name']}"


def primary_element(spirit: dict) -> str:
    elements = spirit.get("elements", [])
    return str(elements[0]) if isinstance(elements, list) and elements else ""


def _normalize_spirit_name(value: str) -> str:
    return re.sub(r"^no\.\d+\s*", "", value.strip(), flags=re.IGNORECASE)


@lru_cache(maxsize=None)
def app_icon(name: str) -> QIcon:
    path = V2_ICONS_DIR / f"{name}.svg"
    return QIcon(str(path)) if path.exists() else QIcon()


@lru_cache(maxsize=None)
def element_icon(element: str) -> QIcon:
    path = ICONS_DIR / f"{element}.png"
    return QIcon(str(path)) if path.exists() else QIcon()


@lru_cache(maxsize=1)
def _spirit_icon_index() -> tuple[dict[tuple[str, str], Path], dict[str, Path]]:
    by_season: dict[tuple[str, str], Path] = {}
    fallback: dict[str, Path] = {}
    if not SPIRITS_DIR.is_dir():
        return by_season, fallback
    for path in SPIRITS_DIR.rglob("*.png"):
        season = path.parent.name if path.parent != SPIRITS_DIR else ""
        name = _normalize_spirit_name(path.stem)
        if name:
            by_season[(season, name)] = path
            fallback.setdefault(name, path)
    return by_season, fallback


@lru_cache(maxsize=256)
def spirit_icon(spirit_name: str, season: str = "") -> QIcon:
    lookup = _normalize_spirit_name(spirit_name)
    by_season, fallback = _spirit_icon_index()
    path = by_season.get((season, lookup)) if season else None
    path = path or fallback.get(lookup)
    return QIcon(str(path)) if path else QIcon()


def version_tuple(version: str) -> tuple[int, int, int] | None:
    normalized = version.strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    normalized = re.split(r"[-+]", normalized, maxsplit=1)[0]
    parts = normalized.split(".")
    if not parts or len(parts) > 3 or any(not part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def is_newer_version(remote_version: str, current_version: str) -> bool:
    remote = version_tuple(remote_version)
    current = version_tuple(current_version)
    return remote is not None and current is not None and remote > current

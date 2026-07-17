"""赛季配置读取工具。"""
from __future__ import annotations

from src.content.repository import get_content_repository


def load_seasons() -> list[dict]:
    """读取内置赛季，并用已启用的本地资源包进行补充或覆盖。"""
    return get_content_repository().load_seasons()


def get_latest_season() -> dict | None:
    """返回编号最大的赛季配置；没有赛季配置时返回 None。"""
    seasons = load_seasons()
    if not seasons:
        return None
    return seasons[-1]

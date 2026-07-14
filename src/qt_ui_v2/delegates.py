"""Painted list delegates keep dense pages fast and visually consistent."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, PITY_MAX, PITY_WARN_THRESHOLD
from src.qt_ui_v2.models import LOG_POOL_ROLE, SPIRIT_COUNT_ROLE, SPIRIT_DATA_ROLE


def _semantic_colors(light: bool) -> tuple[QColor, QColor]:
    if light:
        return QColor("#b87318"), QColor("#c8495a")
    return QColor("#e0a14a"), QColor("#ed6a78")


class SpiritItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        return QSize(220, 66)

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        item = index.data(SPIRIT_DATA_ROLE) or {}
        count = int(index.data(SPIRIT_COUNT_ROLE) or 0)
        rect = option.rect.adjusted(5, 3, -5, -3)
        palette = option.palette
        light = palette.base().color().lightness() > 150

        if option.state & QStyle.StateFlag.State_Selected:
            background = palette.highlight().color()
        elif option.state & QStyle.StateFlag.State_MouseOver:
            background = palette.alternateBase().color()
        else:
            background = palette.base().color()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 9, 9)

        icon_rect = QRect(rect.left() + 10, rect.top() + 9, 42, 42)
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon:
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        text_left = icon_rect.right() + 11
        count_width = 54
        text_right = rect.right() - count_width - 16
        display = str(item.get("display", ""))
        number, _, name = display.partition(" ")

        title_font = QFont(option.font)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(palette.text().color())
        painter.drawText(
            QRect(text_left, rect.top() + 9, text_right - text_left, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            name or display,
        )

        meta_font = QFont(option.font)
        meta_font.setPointSize(max(8, option.font.pointSize() - 1))
        painter.setFont(meta_font)
        painter.setPen(palette.placeholderText().color())
        elements = "/".join(item.get("elements", [])) or "未知属性"
        painter.drawText(
            QRect(text_left, rect.top() + 32, text_right - text_left, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{number}  ·  {elements}",
        )

        warning, critical = _semantic_colors(light)
        count_color = critical if count >= PITY_MAX else warning if count >= PITY_WARN_THRESHOLD else palette.text().color()
        count_rect = QRect(rect.right() - count_width - 8, rect.top() + 14, count_width, 32)
        pill = QColor(count_color)
        pill.setAlpha(28 if light else 42)
        painter.setBrush(pill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(count_rect, 9, 9)
        count_font = QFont(option.font)
        count_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(count_font)
        painter.setPen(count_color)
        painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, str(count))
        painter.restore()


class ActivityLogDelegate(QStyledItemDelegate):
    POOL_LABELS = {
        POOL_FAMILY: "家族",
        POOL_RANDOM: "随机",
        POOL_ELEMENT: "属性",
    }

    def sizeHint(self, option, index) -> QSize:
        return QSize(250, 58)

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = option.rect.adjusted(5, 4, -5, -4)
        palette = option.palette
        pool = str(index.data(LOG_POOL_ROLE) or "")
        light = palette.base().color().lightness() > 150
        colors = {
            POOL_FAMILY: QColor("#b87318" if light else "#e0a14a"),
            POOL_RANDOM: QColor("#3975dc" if light else "#6f9df7"),
            POOL_ELEMENT: QColor("#178c6d" if light else "#57c7a5"),
        }
        accent = colors.get(pool, palette.placeholderText().color())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.alternateBase().color())
        painter.drawRoundedRect(rect, 8, 8)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRect(rect.left(), rect.top(), 3, rect.height()), 2, 2)

        label_font = QFont(option.font)
        label_font.setPointSize(max(8, option.font.pointSize() - 1))
        label_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(label_font)
        painter.setPen(accent)
        painter.drawText(
            QRect(rect.left() + 11, rect.top() + 6, rect.width() - 20, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.POOL_LABELS.get(pool, "其他"),
        )

        body_font = QFont(option.font)
        body_font.setPointSize(max(8, option.font.pointSize() - 1))
        painter.setFont(body_font)
        painter.setPen(palette.text().color())
        painter.drawText(
            QRect(rect.left() + 11, rect.top() + 25, rect.width() - 20, 21),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
        )
        painter.restore()

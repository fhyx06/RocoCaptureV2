"""Painted list delegates keep dense pages fast and visually consistent."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, PITY_MAX, PITY_WARN_THRESHOLD
from src.qt_ui_v2.models import (
    LOG_POOL_ROLE,
    SHINY_RECORD_ROLE,
    SPIRIT_COUNT_ROLE,
    SPIRIT_DATA_ROLE,
)


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
        light = palette.window().color().lightness() > 150

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


class ShinyRecordDelegate(QStyledItemDelegate):
    POOL_LABELS = {
        POOL_FAMILY: "家族池",
        POOL_RANDOM: "随机池",
        POOL_ELEMENT: "属性池",
    }

    def sizeHint(self, option, index) -> QSize:
        return QSize(360, 126)

    @staticmethod
    def _pool_accent(pool_type: str, light: bool, fallback: QColor) -> QColor:
        colors = {
            POOL_FAMILY: QColor("#b87318" if light else "#e0a14a"),
            POOL_RANDOM: QColor("#3975dc" if light else "#6f9df7"),
            POOL_ELEMENT: QColor("#178c6d" if light else "#57c7a5"),
        }
        return colors.get(pool_type, fallback)

    @staticmethod
    def _draw_badge(
        painter: QPainter,
        text: str,
        x: int,
        y: int,
        max_right: int,
        foreground: QColor,
        background: QColor,
    ) -> int:
        metrics = painter.fontMetrics()
        width = min(metrics.horizontalAdvance(text) + 16, max(0, max_right - x))
        if width < 28:
            return x
        rect = QRect(x, y, width, 23)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(foreground)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, metrics.elidedText(text, Qt.TextElideMode.ElideRight, width - 12))
        return rect.right() + 7

    def paint(self, painter: QPainter, option, index) -> None:
        record = index.data(SHINY_RECORD_ROLE)
        if record is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = option.rect.adjusted(6, 5, -6, -5)
        palette = option.palette
        light = palette.window().color().lightness() > 150
        accent = self._pool_accent(record.pool_type, light, palette.highlight().color())
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        surface = QColor("#ffffff" if light else "#1b202b")
        surface_alt = QColor("#f7f9fc" if light else "#222936")
        selected_surface = QColor("#e5eeff" if light else "#22304d")
        background = selected_surface if selected else surface_alt if hovered else surface
        border = QColor(accent if selected else ("#d8dee8" if light else "#30394a"))
        painter.setPen(QPen(border, 1.4 if selected else 1.0))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRect(rect.left(), rect.top(), 4, rect.height()), 2, 2)

        icon_rect = QRect(rect.left() + 16, rect.top() + 21, 64, 64)
        icon_background = QColor(surface_alt)
        painter.setBrush(icon_background)
        painter.drawRoundedRect(icon_rect, 12, 12)
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon and not icon.isNull():
            icon.paint(painter, icon_rect.adjusted(4, 4, -4, -4), Qt.AlignmentFlag.AlignCenter)
        else:
            placeholder_font = QFont(option.font)
            placeholder_font.setPointSize(17)
            placeholder_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(placeholder_font)
            painter.setPen(accent)
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "异")

        pity_rect = QRect(rect.right() - 72, rect.top() + 18, 60, 70)
        painter.setPen(palette.placeholderText().color())
        meta_font = QFont(option.font)
        meta_font.setPointSize(max(8, option.font.pointSize() - 1))
        painter.setFont(meta_font)
        painter.drawText(
            QRect(pity_rect.left(), pity_rect.top(), pity_rect.width(), 18),
            Qt.AlignmentFlag.AlignCenter,
            "保底",
        )
        value_font = QFont(option.font)
        value_font.setPointSize(22)
        value_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(value_font)
        painter.setPen(accent)
        painter.drawText(
            QRect(pity_rect.left(), pity_rect.top() + 17, pity_rect.width(), 44),
            Qt.AlignmentFlag.AlignCenter,
            str(record.pity_count),
        )

        text_left = icon_rect.right() + 14
        text_right = pity_rect.left() - 10
        display = record.spirit_name or "未知精灵"
        number, separator, name = display.partition(" ")
        title = name if separator else display
        title_font = QFont(option.font)
        title_font.setPointSize(option.font.pointSize() + 1)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(palette.text().color())
        title_text = painter.fontMetrics().elidedText(
            title,
            Qt.TextElideMode.ElideRight,
            max(20, text_right - text_left),
        )
        painter.drawText(
            QRect(text_left, rect.top() + 13, max(20, text_right - text_left), 25),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title_text,
        )

        badge_font = QFont(option.font)
        badge_font.setPointSize(max(8, option.font.pointSize() - 1))
        painter.setFont(badge_font)
        badge_background = QColor(accent)
        badge_background.setAlpha(30 if light else 45)
        badge_x = self._draw_badge(
            painter,
            self.POOL_LABELS.get(record.pool_type, "其他"),
            text_left,
            rect.top() + 43,
            text_right,
            accent,
            badge_background,
        )
        neutral_background = QColor(surface_alt)
        if record.season:
            badge_x = self._draw_badge(
                painter,
                record.season,
                badge_x,
                rect.top() + 43,
                text_right,
                palette.placeholderText().color(),
                neutral_background,
            )
        if record.element:
            self._draw_badge(
                painter,
                record.element,
                badge_x,
                rect.top() + 43,
                text_right,
                palette.placeholderText().color(),
                neutral_background,
            )

        timestamp = record.timestamp[:16] if len(record.timestamp) >= 16 else record.timestamp
        bottom_meta = f"{number}  ·  {timestamp}" if separator else timestamp
        painter.setFont(meta_font)
        painter.setPen(palette.placeholderText().color())
        bottom_text = painter.fontMetrics().elidedText(
            bottom_meta,
            Qt.TextElideMode.ElideRight,
            max(20, text_right - text_left),
        )
        painter.drawText(
            QRect(text_left, rect.top() + 75, max(20, text_right - text_left), 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            bottom_text,
        )
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

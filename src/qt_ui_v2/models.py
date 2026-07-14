"""Lightweight Qt models for the V2 interface."""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM
from src.models.save_slot import ActivityLog, ShinyRecord
from src.qt_ui_v2.resources import spirit_icon


SPIRIT_DATA_ROLE = Qt.ItemDataRole.UserRole + 1
SPIRIT_COUNT_ROLE = Qt.ItemDataRole.UserRole + 2
SPIRIT_ELEMENTS_ROLE = Qt.ItemDataRole.UserRole + 3
SPIRIT_SEASON_ROLE = Qt.ItemDataRole.UserRole + 4
LOG_POOL_ROLE = Qt.ItemDataRole.UserRole + 10
SHINY_INDEX_ROLE = Qt.ItemDataRole.UserRole + 20


class SpiritListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item["display"]
        if role == Qt.ItemDataRole.DecorationRole:
            return spirit_icon(item["display"], item["season"])
        if role == SPIRIT_DATA_ROLE:
            return item
        if role == SPIRIT_COUNT_ROLE:
            return item["count"]
        if role == SPIRIT_ELEMENTS_ROLE:
            return item["elements"]
        if role == SPIRIT_SEASON_ROLE:
            return item["season"]
        if role == Qt.ItemDataRole.ToolTipRole:
            elements = "/".join(item["elements"]) or "未知属性"
            return f"{item['display']} · {elements} · 保底 {item['count']}"
        return None

    def set_items(self, items: list[dict]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def item(self, row: int) -> dict | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def find_row(self, display_name: str) -> int:
        for row, item in enumerate(self._items):
            if item["display"] == display_name:
                return row
        return -1

    def update_count(self, display_name: str, count: int) -> None:
        row = self.find_row(display_name)
        if row < 0:
            return
        self._items[row]["count"] = count
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [SPIRIT_COUNT_ROLE, Qt.ItemDataRole.ToolTipRole])


class ShinyTableModel(QAbstractTableModel):
    HEADERS = ["时间", "池子", "赛季", "精灵", "属性", "保底"]
    POOL_LABELS = {
        POOL_FAMILY: "家族池",
        POOL_RANDOM: "随机池",
        POOL_ELEMENT: "属性池",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[tuple[int, ShinyRecord]] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        source_index, record = self._rows[index.row()]
        if role == SHINY_INDEX_ROLE:
            return source_index
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() == 5:
            return Qt.AlignmentFlag.AlignCenter
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        values = [
            record.timestamp[5:16] if len(record.timestamp) >= 16 else record.timestamp,
            self.POOL_LABELS.get(record.pool_type, "其他"),
            record.season or "—",
            record.spirit_name or "未知精灵",
            record.element or "—",
            str(record.pity_count),
        ]
        return values[index.column()]

    def set_records(self, records: list[ShinyRecord], season: str = "", pool_type: str = "") -> None:
        rows: list[tuple[int, ShinyRecord]] = []
        for index in range(len(records) - 1, -1, -1):
            record = records[index]
            if season and record.season != season:
                continue
            if pool_type and record.pool_type != pool_type:
                continue
            rows.append((index, record))
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class ActivityLogModel(QAbstractListModel):
    def __init__(self, limit: int = 500, parent=None):
        super().__init__(parent)
        self._limit = limit
        self._logs: list[ActivityLog] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._logs)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._logs):
            return None
        log = self._logs[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return log.format_display()
        if role == LOG_POOL_ROLE:
            return log.pool_type
        if role == Qt.ItemDataRole.ToolTipRole:
            return log.format_display()
        return None

    def set_logs(self, logs: list[ActivityLog]) -> None:
        self.beginResetModel()
        self._logs = list(reversed(logs[-self._limit :]))
        self.endResetModel()

    def prepend_logs(self, logs: list[ActivityLog]) -> None:
        if not logs:
            return
        newest = list(reversed(logs))
        self.beginResetModel()
        self._logs = (newest + self._logs)[: self._limit]
        self.endResetModel()


class ActivityFilterModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool_filter = ""

    def set_pool_filter(self, pool_type: str) -> None:
        self._pool_filter = pool_type
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._pool_filter:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        pool_type = index.data(LOG_POOL_ROLE)
        if self._pool_filter == "other":
            return pool_type not in {POOL_FAMILY, POOL_RANDOM, POOL_ELEMENT}
        return pool_type == self._pool_filter

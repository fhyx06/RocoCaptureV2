from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.assets.season_loader import load_seasons
from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.models import SHINY_INDEX_ROLE, ShinyTableModel


class ShinyPage(QWidget):
    manual_add_requested = Signal()
    delete_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._slot: SaveSlot | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("异色记录")
        title.setObjectName("pageTitle")
        subtitle = QLabel("统一查看所有池子的出货记录，通过赛季和池子快速筛选。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        filters = QFrame()
        filters.setObjectName("filterBar")
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(14, 8, 14, 8)
        filter_layout.setSpacing(10)
        filter_layout.addWidget(QLabel("赛季"))
        self.season_combo = QComboBox()
        self.season_combo.addItem("全部赛季", "")
        for season in load_seasons():
            season_id = str(season.get("season", ""))
            self.season_combo.addItem(season_id, season_id)
        self.season_combo.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.season_combo)
        filter_layout.addWidget(QLabel("池子"))
        self.pool_combo = QComboBox()
        self.pool_combo.addItem("全部池子", "")
        self.pool_combo.addItem("家族池", POOL_FAMILY)
        self.pool_combo.addItem("随机池", POOL_RANDOM)
        self.pool_combo.addItem("属性池", POOL_ELEMENT)
        self.pool_combo.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.pool_combo)
        filter_layout.addStretch()
        add_btn = QPushButton("手动添加")
        add_btn.setProperty("role", "primary")
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.setProperty("role", "danger")
        self.delete_btn.setEnabled(False)
        add_btn.clicked.connect(self.manual_add_requested.emit)
        self.delete_btn.clicked.connect(self._emit_delete)
        filter_layout.addWidget(add_btn)
        filter_layout.addWidget(self.delete_btn)
        layout.addWidget(filters)

        self.model = ShinyTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)

    def load_slot(self, slot: SaveSlot) -> None:
        self._slot = slot
        self.refresh()

    def refresh(self, *_args) -> None:
        records = self._slot.shiny_records if self._slot else []
        self.model.set_records(
            records,
            str(self.season_combo.currentData() or ""),
            str(self.pool_combo.currentData() or ""),
        )
        self.delete_btn.setEnabled(False)

    def _on_selection_changed(self, *_args) -> None:
        self.delete_btn.setEnabled(bool(self.table.selectionModel().selectedRows()))

    def _emit_delete(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        source_index = rows[0].data(SHINY_INDEX_ROLE)
        if isinstance(source_index, int):
            self.delete_requested.emit(source_index)

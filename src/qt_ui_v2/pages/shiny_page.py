from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.assets.season_loader import load_seasons
from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.delegates import ShinyRecordDelegate
from src.qt_ui_v2.models import SHINY_INDEX_ROLE, ShinyGridModel


class ShinyPage(QWidget):
    manual_add_requested = Signal()
    delete_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._slot: SaveSlot | None = None
        self._columns = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("异色记录")
        title.setObjectName("pageTitle")
        subtitle = QLabel("收藏每次出货，通过赛季和池子快速找到重要记录。")
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
        self.result_summary = QLabel("0 条记录")
        self.result_summary.setObjectName("muted")
        filter_layout.addWidget(self.result_summary)
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

        self.model = ShinyGridModel(self)
        self.gallery = QTableView()
        self.gallery.setObjectName("shinyGallery")
        self.gallery.setModel(self.model)
        self.gallery.setItemDelegate(ShinyRecordDelegate(self.gallery))
        self.gallery.setShowGrid(False)
        self.gallery.setAlternatingRowColors(False)
        self.gallery.setMouseTracking(True)
        self.gallery.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.gallery.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.gallery.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.gallery.horizontalHeader().setVisible(False)
        self.gallery.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.gallery.verticalHeader().setVisible(False)
        self.gallery.verticalHeader().setDefaultSectionSize(126)
        self.gallery.verticalHeader().setMinimumSectionSize(126)
        self.gallery.selectionModel().selectionChanged.connect(self._on_selection_changed)

        empty_state = QFrame()
        empty_state.setObjectName("emptyState")
        empty_layout = QVBoxLayout(empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addStretch()
        empty_icon = QLabel("✦")
        empty_icon.setObjectName("emptyIcon")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel("还没有异色记录")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_subtitle = QLabel("出货后点击“记录异色”，这里会成为你的收藏册。")
        self.empty_subtitle.setObjectName("muted")
        self.empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_subtitle)
        empty_layout.addStretch()

        self.record_stack = QStackedWidget()
        self.record_stack.setObjectName("shinyStack")
        self.record_stack.addWidget(empty_state)
        self.record_stack.addWidget(self.gallery)
        layout.addWidget(self.record_stack, 1)
        QTimer.singleShot(0, self._relayout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._relayout)

    def _relayout(self) -> None:
        width = max(1, self.gallery.viewport().width())
        columns = 2 if width >= 720 else 1
        if columns == self._columns:
            return
        self._columns = columns
        self.model.set_columns(columns)
        self.gallery.resizeRowsToContents()

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
        count = self.model.record_count()
        self.result_summary.setText(f"{count} 条记录")
        self.gallery.setCurrentIndex(QModelIndex())
        self.gallery.clearSelection()
        self.delete_btn.setEnabled(False)
        if count:
            self.record_stack.setCurrentWidget(self.gallery)
            QTimer.singleShot(0, self._relayout)
        else:
            has_records = bool(records)
            self.empty_title.setText("没有符合筛选的记录" if has_records else "还没有异色记录")
            self.empty_subtitle.setText(
                "换一个赛季或池子筛选试试。"
                if has_records
                else "出货后点击“记录异色”，这里会成为你的收藏册。"
            )
            self.record_stack.setCurrentIndex(0)

    def _on_selection_changed(self, *_args) -> None:
        self.delete_btn.setEnabled(bool(self.gallery.selectionModel().selectedIndexes()))

    def _emit_delete(self) -> None:
        indexes = self.gallery.selectionModel().selectedIndexes()
        if not indexes:
            return
        source_index = indexes[0].data(SHINY_INDEX_ROLE)
        if isinstance(source_index, int):
            self.delete_requested.emit(source_index)

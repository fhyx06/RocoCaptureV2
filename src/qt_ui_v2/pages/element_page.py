from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.models.constants import ELEMENTS, PITY_MAX, PITY_WARN_THRESHOLD
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.resources import element_icon
from src.qt_ui_v2.theme import repolish


class ElementPage(QWidget):
    increase_requested = Signal(str)
    decrease_requested = Signal(str)
    reset_requested = Signal(str)
    shiny_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._slot: SaveSlot | None = None
        self._selected = ""
        self._columns = 0
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("属性池")
        title.setObjectName("pageTitle")
        subtitle = QLabel("18 种属性分别记录保底，复合属性按第一属性计算。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.grid_host = QWidget()
        self.grid_layout = QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 8, 0)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)
        for element in ELEMENTS:
            button = QPushButton(f"{element}\n保底 0")
            button.setObjectName("elementCard")
            button.setCheckable(True)
            button.setIcon(element_icon(element))
            button.setIconSize(QSize(28, 28))
            button.clicked.connect(lambda _checked=False, name=element: self.select_element(name))
            self._buttons[element] = button
        self.scroll.setWidget(self.grid_host)
        splitter.addWidget(self.scroll)

        detail = QFrame()
        detail.setObjectName("detailCard")
        detail.setMinimumWidth(270)
        detail.setMaximumWidth(340)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(22, 22, 22, 22)
        detail_layout.setSpacing(12)
        self.detail_title = QLabel("请选择属性")
        self.detail_title.setObjectName("detailTitle")
        self.detail_meta = QLabel("从左侧选择需要记录的属性")
        self.detail_meta.setObjectName("detailMeta")
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setObjectName("countValue")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption = QLabel("当前保底")
        caption.setObjectName("countCaption")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.count_label)
        detail_layout.addWidget(caption)
        detail_layout.addSpacing(10)

        row1 = QHBoxLayout()
        self.increase_btn = QPushButton("+1")
        self.increase_btn.setProperty("role", "primary")
        self.decrease_btn = QPushButton("-1")
        row1.addWidget(self.increase_btn, 2)
        row1.addWidget(self.decrease_btn, 1)
        detail_layout.addLayout(row1)
        row2 = QHBoxLayout()
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setProperty("role", "danger")
        self.shiny_btn = QPushButton("记录异色")
        self.shiny_btn.setProperty("role", "shiny")
        row2.addWidget(self.reset_btn)
        row2.addWidget(self.shiny_btn)
        detail_layout.addLayout(row2)
        self.increase_btn.clicked.connect(lambda: self.increase_requested.emit(self._selected))
        self.decrease_btn.clicked.connect(lambda: self.decrease_requested.emit(self._selected))
        self.reset_btn.clicked.connect(lambda: self.reset_requested.emit(self._selected))
        self.shiny_btn.clicked.connect(lambda: self.shiny_requested.emit(self._selected))
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([640, 300])
        layout.addWidget(splitter, 1)
        self._set_actions_enabled(False)
        QTimer.singleShot(0, self._relayout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._relayout)

    def _relayout(self) -> None:
        width = max(1, self.scroll.viewport().width())
        columns = 2 if width < 480 else 3 if width < 700 else 4 if width < 920 else 5
        if columns == self._columns:
            return
        self._columns = columns
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        for index in range(len(ELEMENTS) + 1):
            self.grid_layout.setColumnStretch(index, 0)
            self.grid_layout.setRowStretch(index, 0)
        for index, element in enumerate(ELEMENTS):
            row, column = divmod(index, columns)
            self.grid_layout.addWidget(self._buttons[element], row, column)
        for column in range(columns):
            self.grid_layout.setColumnStretch(column, 1)
        self.grid_layout.setRowStretch((len(ELEMENTS) + columns - 1) // columns, 1)

    def load_slot(self, slot: SaveSlot) -> None:
        self._slot = slot
        for element in ELEMENTS:
            self.update_count(element, slot.element_pool.get(element, 0))
        if self._selected:
            self.select_element(self._selected)

    def select_element(self, element: str) -> None:
        self._selected = element
        for name, button in self._buttons.items():
            button.setChecked(name == element)
        self.detail_title.setText(element)
        self.detail_meta.setText("属性池保底进度")
        count = self._slot.element_pool.get(element, 0) if self._slot else 0
        self._set_detail_count(count)
        self._set_actions_enabled(True)

    def update_count(self, element: str, count: int) -> None:
        button = self._buttons.get(element)
        if button:
            button.setText(f"{element}\n保底 {count}")
            state = "critical" if count >= PITY_MAX else "warn" if count >= PITY_WARN_THRESHOLD else "normal"
            button.setProperty("state", state)
            repolish(button)
        if self._selected == element:
            self._set_detail_count(count)

    def _set_detail_count(self, count: int) -> None:
        self.count_label.setText(str(count))
        state = "critical" if count >= PITY_MAX else "warn" if count >= PITY_WARN_THRESHOLD else "normal"
        self.count_label.setProperty("state", state)
        repolish(self.count_label)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for button in (self.increase_btn, self.decrease_btn, self.reset_btn, self.shiny_btn):
            button.setEnabled(enabled)

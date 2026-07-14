from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.models.constants import PITY_MAX, PITY_WARN_THRESHOLD
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.theme import repolish


class RandomPage(QWidget):
    increase_requested = Signal(str)
    decrease_requested = Signal()
    reset_requested = Signal()
    shiny_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("随机池")
        title.setObjectName("pageTitle")
        subtitle = QLabel("记录随机捕捉次数，可选填精灵名称作为操作备注。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(18)
        counter_card = QFrame()
        counter_card.setObjectName("detailCard")
        counter_card.setMinimumWidth(320)
        counter_layout = QVBoxLayout(counter_card)
        counter_layout.setContentsMargins(28, 28, 28, 28)
        counter_layout.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setObjectName("countValue")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption = QLabel("随机池当前保底")
        caption.setObjectName("countCaption")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        counter_layout.addWidget(self.count_label)
        counter_layout.addWidget(caption)
        counter_layout.addStretch()
        content.addWidget(counter_card, 2)

        action_card = QFrame()
        action_card.setObjectName("detailCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(24, 24, 24, 24)
        action_layout.setSpacing(12)
        action_title = QLabel("快速记录")
        action_title.setObjectName("detailTitle")
        action_hint = QLabel("输入名称后按回车，也可以直接点击 +1。")
        action_hint.setObjectName("detailMeta")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("精灵名称（可选）")
        self.name_edit.returnPressed.connect(self._emit_increase)
        action_layout.addWidget(action_title)
        action_layout.addWidget(action_hint)
        action_layout.addSpacing(8)
        action_layout.addWidget(self.name_edit)

        first_row = QHBoxLayout()
        increase = QPushButton("+1")
        increase.setProperty("role", "primary")
        decrease = QPushButton("-1")
        first_row.addWidget(increase, 2)
        first_row.addWidget(decrease, 1)
        action_layout.addLayout(first_row)
        second_row = QHBoxLayout()
        reset = QPushButton("重置")
        reset.setProperty("role", "danger")
        shiny = QPushButton("记录异色")
        shiny.setProperty("role", "shiny")
        second_row.addWidget(reset)
        second_row.addWidget(shiny)
        action_layout.addLayout(second_row)
        action_layout.addStretch()
        increase.clicked.connect(self._emit_increase)
        decrease.clicked.connect(self.decrease_requested.emit)
        reset.clicked.connect(self.reset_requested.emit)
        shiny.clicked.connect(self.shiny_requested.emit)
        content.addWidget(action_card, 3)
        layout.addLayout(content, 1)

    def load_slot(self, slot: SaveSlot) -> None:
        self.update_count(slot.random_pool)

    def update_count(self, count: int) -> None:
        self.count_label.setText(str(count))
        state = "critical" if count >= PITY_MAX else "warn" if count >= PITY_WARN_THRESHOLD else "normal"
        self.count_label.setProperty("state", state)
        repolish(self.count_label)

    def _emit_increase(self) -> None:
        name = self.name_edit.text().strip()
        self.name_edit.clear()
        self.increase_requested.emit(name)

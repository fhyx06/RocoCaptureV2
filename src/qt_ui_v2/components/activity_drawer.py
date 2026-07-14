from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QListView, QPushButton, QVBoxLayout, QWidget

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM
from src.models.save_slot import ActivityLog
from src.qt_ui_v2.delegates import ActivityLogDelegate
from src.qt_ui_v2.models import ActivityFilterModel, ActivityLogModel


class ActivityDrawer(QFrame):
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("activityDrawer")
        self.setFixedWidth(310)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("活动日志")
        title.setObjectName("detailTitle")
        close = QPushButton("关闭")
        close.clicked.connect(self.close_requested.emit)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        layout.addLayout(header)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部日志", "")
        self.filter_combo.addItem("家族池", POOL_FAMILY)
        self.filter_combo.addItem("随机池", POOL_RANDOM)
        self.filter_combo.addItem("属性池", POOL_ELEMENT)
        self.filter_combo.addItem("其他", "other")
        layout.addWidget(self.filter_combo)

        self.source_model = ActivityLogModel(parent=self)
        self.filter_model = ActivityFilterModel(self)
        self.filter_model.setSourceModel(self.source_model)
        self.filter_combo.currentIndexChanged.connect(
            lambda _index: self.filter_model.set_pool_filter(str(self.filter_combo.currentData() or ""))
        )
        self.list_view = QListView()
        self.list_view.setModel(self.filter_model)
        self.list_view.setItemDelegate(ActivityLogDelegate(self.list_view))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list_view.setMouseTracking(True)
        layout.addWidget(self.list_view, 1)

        note = QLabel("最多显示最近 500 条，完整日志保存在存档中。")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

    def set_logs(self, logs: list[ActivityLog]) -> None:
        self.source_model.set_logs(logs)

    def prepend_logs(self, logs: list[ActivityLog]) -> None:
        self.source_model.prepend_logs(logs)

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QSplitter,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from src.assets.season_loader import load_seasons
from src.models.constants import PITY_MAX, PITY_WARN_THRESHOLD
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.delegates import SpiritItemDelegate
from src.qt_ui_v2.models import SPIRIT_DATA_ROLE, SpiritListModel
from src.qt_ui_v2.resources import spirit_display, spirit_icon
from src.qt_ui_v2.theme import repolish


class FamilyPage(QWidget):
    increase_requested = Signal(str)
    decrease_requested = Signal(str)
    reset_requested = Signal(str)
    shiny_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._slot: SaveSlot | None = None
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self._pending_spirit = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("家族池")
        title.setObjectName("pageTitle")
        subtitle = QLabel("选择赛季与精灵，快速记录最常用的家族池保底。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QFrame()
        controls.setObjectName("filterBar")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(14, 8, 14, 8)
        controls_layout.setSpacing(12)
        self.season_tabs = QTabBar()
        self.season_tabs.setExpanding(False)
        self.season_tabs.setDrawBase(False)
        for season in self._seasons:
            season_id = str(season.get("season", ""))
            index = self.season_tabs.addTab(season_id)
            self.season_tabs.setTabData(index, season_id)
        self.season_tabs.currentChanged.connect(self._on_season_changed)
        controls_layout.addWidget(self.season_tabs)
        controls_layout.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索编号或精灵名称")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(220)
        self.search_edit.textChanged.connect(self._refresh_model)
        controls_layout.addWidget(self.search_edit)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部精灵", "all")
        self.filter_combo.addItem("已有进度", "active")
        self.filter_combo.addItem("接近保底", "warning")
        self.filter_combo.currentIndexChanged.connect(self._refresh_model)
        controls_layout.addWidget(self.filter_combo)
        layout.addWidget(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)

        list_column = QWidget()
        list_layout = QVBoxLayout(list_column)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)
        self.summary_label = QLabel("0 只精灵")
        self.summary_label.setObjectName("muted")
        list_layout.addWidget(self.summary_label)
        self.model = SpiritListModel(self)
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(SpiritItemDelegate(self.list_view))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setMouseTracking(True)
        self.list_view.setUniformItemSizes(True)
        self.list_view.selectionModel().currentChanged.connect(self._on_selected)
        list_layout.addWidget(self.list_view, 1)
        splitter.addWidget(list_column)

        detail = QFrame()
        detail.setObjectName("detailCard")
        detail.setMinimumWidth(300)
        detail.setMaximumWidth(370)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(22, 22, 22, 22)
        detail_layout.setSpacing(12)
        self.detail_title = QLabel("请选择精灵")
        self.detail_title.setObjectName("detailTitle")
        self.detail_number = QLabel("从左侧列表选择要记录的精灵")
        self.detail_number.setObjectName("detailMeta")
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_number)

        self.element_row = QHBoxLayout()
        self.element_row.setSpacing(6)
        self.element_badges: list[QLabel] = []
        for _ in range(2):
            badge = QLabel()
            badge.setObjectName("badge")
            badge.hide()
            self.element_badges.append(badge)
            self.element_row.addWidget(badge)
        self.element_row.addStretch()
        detail_layout.addLayout(self.element_row)

        self.detail_icon = QLabel()
        self.detail_icon.setObjectName("spiritHero")
        self.detail_icon.setMinimumHeight(180)
        self.detail_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.detail_icon, 1)

        self.count_label = QLabel("0")
        self.count_label.setObjectName("countValue")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_caption = QLabel("当前保底")
        count_caption.setObjectName("countCaption")
        count_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.count_label)
        detail_layout.addWidget(count_caption)
        detail_layout.addSpacing(10)

        first_row = QHBoxLayout()
        self.increase_btn = QPushButton("+1")
        self.increase_btn.setProperty("role", "primary")
        self.decrease_btn = QPushButton("-1")
        first_row.addWidget(self.increase_btn, 2)
        first_row.addWidget(self.decrease_btn, 1)
        detail_layout.addLayout(first_row)

        second_row = QHBoxLayout()
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setProperty("role", "danger")
        self.shiny_btn = QPushButton("记录异色")
        self.shiny_btn.setProperty("role", "shiny")
        second_row.addWidget(self.reset_btn)
        second_row.addWidget(self.shiny_btn)
        detail_layout.addLayout(second_row)
        self.increase_btn.clicked.connect(self._emit_increase)
        self.decrease_btn.clicked.connect(self._emit_decrease)
        self.reset_btn.clicked.connect(self._emit_reset)
        self.shiny_btn.clicked.connect(self._emit_shiny)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([620, 340])
        layout.addWidget(splitter, 1)
        self._set_actions_enabled(False)

    def load_slot(self, slot: SaveSlot, selection: dict | None = None) -> None:
        self._slot = slot
        selection = selection or {}
        season_id = str(selection.get("season", ""))
        self._pending_spirit = str(selection.get("spirit", ""))
        if season_id:
            for index in range(self.season_tabs.count()):
                if self.season_tabs.tabData(index) == season_id:
                    self.season_tabs.setCurrentIndex(index)
                    break
        self._refresh_model()

    def selection_state(self) -> dict[str, str]:
        item = self._selected_item()
        return {
            "season": self.current_season(),
            "spirit": str(item.get("display", "")) if item else "",
        }

    def current_season(self) -> str:
        return str(self.season_tabs.tabData(self.season_tabs.currentIndex()) or "")

    def update_count(self, display_name: str, count: int) -> None:
        self.model.update_count(display_name, count)
        item = self._selected_item()
        if item and item.get("display") == display_name:
            item["count"] = count
            self._set_count(count)
        self._update_summary()

    def _on_season_changed(self, _index: int) -> None:
        self._pending_spirit = ""
        self._refresh_model()

    def _refresh_model(self, *_args) -> None:
        if self._slot is None:
            return
        preserve = self._pending_spirit
        current = self._selected_item()
        if not preserve and current:
            preserve = str(current.get("display", ""))

        query = self.search_edit.text().strip().lower()
        filter_mode = str(self.filter_combo.currentData() or "all")
        season_id = self.current_season()
        season = self._season_by_id.get(season_id, {})
        items: list[dict] = []
        for spirit in season.get("spirits", []):
            display = spirit_display(spirit)
            count = self._slot.family_pool.get(display, 0)
            if query and query not in display.lower():
                continue
            if filter_mode == "active" and count <= 0:
                continue
            if filter_mode == "warning" and count < PITY_WARN_THRESHOLD:
                continue
            items.append({
                "display": display,
                "season": season_id,
                "elements": list(spirit.get("elements", [])),
                "count": count,
            })
        self.model.set_items(items)
        self._pending_spirit = ""
        row = self.model.find_row(preserve) if preserve else -1
        if row < 0 and items:
            row = 0
        if row >= 0:
            index = self.model.index(row, 0)
            self.list_view.setCurrentIndex(index)
        else:
            self.list_view.setCurrentIndex(QModelIndex())
            self._show_item(None)
        self._update_summary()

    def _update_summary(self) -> None:
        total = self.model.rowCount()
        active = sum(1 for row in range(total) if int(self.model.item(row).get("count", 0)) > 0)
        self.summary_label.setText(f"{total} 只精灵  ·  {active} 个已有进度")

    def _selected_item(self) -> dict | None:
        index = self.list_view.currentIndex()
        return index.data(SPIRIT_DATA_ROLE) if index.isValid() else None

    def _on_selected(self, current: QModelIndex, _previous: QModelIndex) -> None:
        self._show_item(current.data(SPIRIT_DATA_ROLE) if current.isValid() else None)

    def _show_item(self, item: dict | None) -> None:
        self._set_actions_enabled(item is not None)
        if not item:
            self.detail_title.setText("请选择精灵")
            self.detail_number.setText("从左侧列表选择要记录的精灵")
            self.detail_icon.clear()
            self._set_count(0)
            for badge in self.element_badges:
                badge.hide()
            return
        number, _, name = str(item["display"]).partition(" ")
        self.detail_title.setText(name or item["display"])
        self.detail_number.setText(f"{number}  ·  {item['season']}")
        self.detail_icon.setPixmap(spirit_icon(item["display"], item["season"]).pixmap(160, 160))
        elements = item.get("elements", [])
        for index, badge in enumerate(self.element_badges):
            if index < len(elements):
                badge.setText(str(elements[index]))
                badge.show()
            else:
                badge.hide()
        self._set_count(int(item.get("count", 0)))

    def _set_count(self, count: int) -> None:
        self.count_label.setText(str(count))
        state = "critical" if count >= PITY_MAX else "warn" if count >= PITY_WARN_THRESHOLD else "normal"
        self.count_label.setProperty("state", state)
        repolish(self.count_label)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for button in (self.increase_btn, self.decrease_btn, self.reset_btn, self.shiny_btn):
            button.setEnabled(enabled)

    def _emit_increase(self) -> None:
        item = self._selected_item()
        if item:
            self.increase_requested.emit(item["display"])

    def _emit_decrease(self) -> None:
        item = self._selected_item()
        if item:
            self.decrease_requested.emit(item["display"])

    def _emit_reset(self) -> None:
        item = self._selected_item()
        if item:
            self.reset_requested.emit(item["display"])

    def _emit_shiny(self) -> None:
        item = self._selected_item()
        if item:
            self.shiny_requested.emit(item["display"], item["season"])

"""Dialogs shared by the V2 pool pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.assets.season_loader import get_latest_season, load_seasons
from src.models.constants import ELEMENTS, POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, POOL_UNKNOWN
from src.models.save_slot import SaveSlot
from src.qt_ui_v2.resources import element_icon, primary_element, spirit_display, spirit_icon


class ShinyChoiceDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        pool_type: str,
        pity_count: int,
        fixed_spirit: str = "",
        fixed_season: str = "",
        element: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("记录异色")
        self.setMinimumWidth(380)
        self._pool_type = pool_type
        self._pity_count = pity_count
        self._fixed_spirit = fixed_spirit
        self._fixed_season = fixed_season
        self._element = element
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.addRow("当前保底", QLabel(str(pity_count)))

        if element:
            element_row = QWidget()
            element_layout = QHBoxLayout(element_row)
            element_layout.setContentsMargins(0, 0, 0, 0)
            element_layout.setSpacing(7)
            element_badge = QLabel()
            element_badge.setPixmap(element_icon(element).pixmap(20, 20))
            element_layout.addWidget(element_badge)
            element_layout.addWidget(QLabel(element))
            element_layout.addStretch()
            form.addRow("属性", element_row)

        if fixed_spirit:
            form.addRow("赛季", QLabel(fixed_season or "未知赛季"))
            form.addRow("精灵", QLabel(fixed_spirit))
        else:
            self.season_combo = QComboBox()
            for season in self._seasons:
                self.season_combo.addItem(str(season.get("season", "")))
            latest = get_latest_season()
            if latest:
                self.season_combo.setCurrentText(str(latest.get("season", "")))
            self.season_combo.currentTextChanged.connect(self._refresh_spirits)
            form.addRow("赛季", self.season_combo)

            self.spirit_combo = QComboBox()
            form.addRow("精灵", self.spirit_combo)
            self._refresh_spirits(self.season_combo.currentText())

        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        confirm = QPushButton("记录并清空")
        confirm.setProperty("role", "shiny")
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self._accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

    def _refresh_spirits(self, season_id: str) -> None:
        if not hasattr(self, "spirit_combo"):
            return
        self.spirit_combo.clear()
        spirits = self._season_by_id.get(season_id, {}).get("spirits", [])
        if self._pool_type == POOL_ELEMENT and self._element:
            spirits = [item for item in spirits if primary_element(item) == self._element]
        for spirit in spirits:
            self.spirit_combo.addItem(spirit_icon(spirit["name"], season_id), spirit_display(spirit))

    def _accept(self) -> None:
        if self._pity_count <= 0:
            QMessageBox.warning(self, "无法记录异色", "当前保底为 0。")
            return
        if self._fixed_spirit:
            season, spirit = self._fixed_season, self._fixed_spirit
        else:
            season, spirit = self.season_combo.currentText(), self.spirit_combo.currentText()
        if not spirit:
            return
        self.result_data = {
            "pool_type": self._pool_type,
            "season": season,
            "spirit_name": spirit,
            "element": self._element,
            "pity_count": self._pity_count,
            "reset_after_record": True,
        }
        self.accept()


class ManualShinyDialog(QDialog):
    POOL_LABELS = {
        POOL_RANDOM: "随机池",
        POOL_FAMILY: "家族池",
        POOL_ELEMENT: "属性池",
        POOL_UNKNOWN: "其他",
    }

    def __init__(self, parent: QWidget, slot: SaveSlot):
        super().__init__(parent)
        self.setWindowTitle("手动添加异色记录")
        self.setMinimumWidth(420)
        self._slot = slot
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.pool_combo = QComboBox()
        for key, label in self.POOL_LABELS.items():
            self.pool_combo.addItem(label, key)
        self.pool_combo.currentIndexChanged.connect(self._refresh_form)
        form.addRow("池子", self.pool_combo)

        self.season_combo = QComboBox()
        for season in self._seasons:
            self.season_combo.addItem(str(season.get("season", "")))
        latest = get_latest_season()
        if latest:
            self.season_combo.setCurrentText(str(latest.get("season", "")))
        self.season_combo.currentTextChanged.connect(self._refresh_spirits)
        form.addRow("赛季", self.season_combo)

        self.element_combo = QComboBox()
        for element in ELEMENTS:
            self.element_combo.addItem(element_icon(element), element)
        self.element_combo.currentTextChanged.connect(self._refresh_form)
        form.addRow("属性", self.element_combo)

        self.spirit_combo = QComboBox()
        self.spirit_combo.currentIndexChanged.connect(self._refresh_pity)
        form.addRow("精灵", self.spirit_combo)

        self.pity_spin = QSpinBox()
        self.pity_spin.setRange(1, 999)
        form.addRow("保底数", self.pity_spin)

        self.reset_check = QCheckBox("记录后清空对应保底")
        self.reset_check.setChecked(True)
        form.addRow("", self.reset_check)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        confirm = QPushButton("添加记录")
        confirm.setProperty("role", "primary")
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self._accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

        self._refresh_spirits(self.season_combo.currentText())
        self._refresh_form()

    def _refresh_form(self) -> None:
        pool_type = self.pool_combo.currentData()
        self.element_combo.setEnabled(pool_type == POOL_ELEMENT)
        self.reset_check.setEnabled(pool_type != POOL_UNKNOWN)
        self.reset_check.setChecked(pool_type != POOL_UNKNOWN)
        self._refresh_spirits(self.season_combo.currentText())

    def _refresh_spirits(self, season_id: str) -> None:
        self.spirit_combo.blockSignals(True)
        self.spirit_combo.clear()
        spirits = self._season_by_id.get(season_id, {}).get("spirits", [])
        if self.pool_combo.currentData() == POOL_ELEMENT:
            element = self.element_combo.currentText()
            spirits = [item for item in spirits if primary_element(item) == element]
        for spirit in spirits:
            self.spirit_combo.addItem(spirit_icon(spirit["name"], season_id), spirit_display(spirit))
        self.spirit_combo.blockSignals(False)
        self._refresh_pity()

    def _refresh_pity(self) -> None:
        pool_type = self.pool_combo.currentData()
        if pool_type == POOL_RANDOM:
            count = self._slot.random_pool
        elif pool_type == POOL_FAMILY:
            count = self._slot.family_pool.get(self.spirit_combo.currentText(), 0)
        elif pool_type == POOL_ELEMENT:
            count = self._slot.element_pool.get(self.element_combo.currentText(), 0)
        else:
            count = 1
        self.pity_spin.setValue(max(1, count))

    def _accept(self) -> None:
        pool_type = str(self.pool_combo.currentData())
        spirit = self.spirit_combo.currentText()
        if not spirit:
            return
        self.result_data = {
            "pool_type": pool_type,
            "season": self.season_combo.currentText(),
            "spirit_name": spirit,
            "element": self.element_combo.currentText() if pool_type == POOL_ELEMENT else "",
            "pity_count": self.pity_spin.value(),
            "reset_after_record": self.reset_check.isChecked() if pool_type != POOL_UNKNOWN else False,
        }
        self.accept()

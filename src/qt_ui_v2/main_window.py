"""Main window for the redesigned V2 interface."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.__about__ import (
    APP_DISPLAY_NAME,
    APP_NAME,
    APP_VERSION,
    GITHUB_PROJECT_URL,
    GITHUB_RELEASES_URL,
    UPDATE_MANIFEST_URL,
)
from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, POOL_UNKNOWN
from src.models.save_slot import ActivityLog, SaveSlot
from src.qt_ui_v2.components.activity_drawer import ActivityDrawer
from src.qt_ui_v2.dialogs import ManualShinyDialog, ShinyChoiceDialog
from src.qt_ui_v2.pages.element_page import ElementPage
from src.qt_ui_v2.pages.family_page import FamilyPage
from src.qt_ui_v2.pages.random_page import RandomPage
from src.qt_ui_v2.pages.settings_page import SettingsPage
from src.qt_ui_v2.pages.shiny_page import ShinyPage
from src.qt_ui_v2.resources import ICONS_DIR, app_icon, is_newer_version
from src.qt_ui_v2.theme import apply_theme
from src.services.save_service import SaveService
from src.services.content_pack_service import ContentPackError, ContentPackService
from src.services.settings_service import THEME_DARK, SettingsService
from src.utils.beep import beep


PAGE_FAMILY = 0
PAGE_RANDOM = 1
PAGE_ELEMENT = 2
PAGE_SHINY = 3
PAGE_SETTINGS = 4
PAGE_COUNT = 5


class QtMainWindowV2(QMainWindow):
    def __init__(
        self,
        save_service: SaveService,
        settings_service: SettingsService,
        content_pack_service: ContentPackService | None = None,
    ):
        super().__init__()
        self._save_svc = save_service
        self._settings_svc = settings_service
        self._content_svc = content_pack_service
        self._ui_state = settings_service.ui_state()
        self._family_selections = dict(self._ui_state.get("family_selections", {}))
        self._pages: dict[int, QWidget] = {}
        self._page_builders = {
            PAGE_FAMILY: self._create_family_page,
            PAGE_RANDOM: self._create_random_page,
            PAGE_ELEMENT: self._create_element_page,
            PAGE_SHINY: self._create_shiny_page,
            PAGE_SETTINGS: self._create_settings_page,
        }
        self._nav_buttons: dict[int, QPushButton] = {}
        self._current_page = PAGE_FAMILY
        self._network_module = None
        self._network_manager = None
        self._update_reply = None

        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
        icon_path = ICONS_DIR / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._build_shell()

        saves = self._save_svc.list_saves()
        if saves:
            self._switch_save(saves[0])
        self._refresh_save_combo()
        self._set_page(PAGE_FAMILY)
        self._update_theme_controls()

    def _build_shell(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self._top_bar = self._build_top_bar()
        root_layout.addWidget(self._top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        page_host = QWidget()
        page_host.setObjectName("pageHost")
        page_layout = QVBoxLayout(page_host)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.page_stack = QStackedWidget()
        for index in range(PAGE_COUNT):
            if index == PAGE_FAMILY:
                page = self._create_family_page()
                self._pages[index] = page
            else:
                page = QWidget()
                page.setObjectName("lazyPagePlaceholder")
            self.page_stack.addWidget(page)
        page_layout.addWidget(self.page_stack)
        body.addWidget(page_host, 1)

        self.activity_drawer = ActivityDrawer(root)
        self.activity_drawer.hide()
        self.activity_drawer.close_requested.connect(lambda: self._set_activity_visible(False))
        root_layout.addLayout(body, 1)
        self.setCentralWidget(root)
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)

    def _build_top_bar(self) -> QWidget:
        top = QWidget()
        top.setObjectName("topBar")
        layout = QHBoxLayout(top)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)
        brand = QLabel(APP_DISPLAY_NAME)
        brand.setObjectName("brand")
        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("version")
        layout.addWidget(brand)
        layout.addWidget(version)
        layout.addSpacing(18)
        save_label = QLabel("存档")
        save_label.setObjectName("muted")
        layout.addWidget(save_label)
        self.save_combo = QComboBox()
        self.save_combo.setMinimumWidth(170)
        self.save_combo.currentTextChanged.connect(self._on_save_selected)
        layout.addWidget(self.save_combo)

        manage = QToolButton()
        manage.setText("存档管理")
        manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(manage)
        for text, handler in (
            ("新建存档", self._create_save),
            ("重命名当前存档", self._rename_save),
            ("导入存档", self._import_save),
            ("导出当前存档", self._export_save),
        ):
            action = QAction(text, menu)
            action.triggered.connect(handler)
            menu.addAction(action)
        menu.addSeparator()
        delete_action = QAction("删除当前存档", menu)
        delete_action.triggered.connect(self._delete_save)
        menu.addAction(delete_action)
        manage.setMenu(menu)
        layout.addWidget(manage)
        layout.addStretch()

        self.random_quick_btn = QPushButton("随机池  0")
        self.random_quick_btn.setObjectName("randomQuick")
        self.random_quick_btn.setIcon(app_icon("random"))
        self.random_quick_btn.clicked.connect(lambda: self._set_page(PAGE_RANDOM))
        layout.addWidget(self.random_quick_btn)
        self.activity_btn = QPushButton("活动")
        self.activity_btn.setCheckable(True)
        self.activity_btn.setIcon(app_icon("activity"))
        self.activity_btn.clicked.connect(self._set_activity_visible)
        layout.addWidget(self.activity_btn)
        self.theme_btn = QPushButton("浅色主题")
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)
        return top

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(174)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 18, 10, 14)
        layout.setSpacing(6)
        group = QButtonGroup(self)
        group.setExclusive(True)
        navigation = (
            (PAGE_FAMILY, "family", "家族池"),
            (PAGE_RANDOM, "random", "随机池"),
            (PAGE_ELEMENT, "element", "属性池"),
            (PAGE_SHINY, "shiny", "异色记录"),
        )
        for index, icon_name, label in navigation:
            button = self._nav_button(icon_name, label)
            group.addButton(button, index)
            self._nav_buttons[index] = button
            layout.addWidget(button)
        layout.addStretch()
        settings = self._nav_button("settings", "设置")
        group.addButton(settings, PAGE_SETTINGS)
        self._nav_buttons[PAGE_SETTINGS] = settings
        layout.addWidget(settings)
        group.idClicked.connect(self._set_page)
        self._nav_group = group
        return sidebar

    @staticmethod
    def _nav_button(icon_name: str, label: str) -> QPushButton:
        button = QPushButton(app_icon(icon_name), label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setIconSize(QSize(20, 20))
        return button

    def _ensure_page(self, index: int) -> QWidget:
        if index in self._pages:
            return self._pages[index]
        placeholder = self.page_stack.widget(index)
        page = self._page_builders[index]()
        self.page_stack.removeWidget(placeholder)
        placeholder.deleteLater()
        self.page_stack.insertWidget(index, page)
        self._pages[index] = page
        slot = self._save_svc.current
        if slot:
            self._refresh_page(index, slot)
        return page

    def _set_page(self, index: int) -> None:
        if not 0 <= index < PAGE_COUNT:
            return
        self._ensure_page(index)
        self.page_stack.setCurrentIndex(index)
        self._current_page = index
        button = self._nav_buttons.get(index)
        if button:
            button.setChecked(True)

    def _create_family_page(self) -> FamilyPage:
        page = FamilyPage()
        page.increase_requested.connect(self._family_increase)
        page.decrease_requested.connect(self._family_decrease)
        page.reset_requested.connect(self._family_reset)
        page.shiny_requested.connect(self._family_shiny)
        return page

    def _create_random_page(self) -> RandomPage:
        page = RandomPage()
        page.increase_requested.connect(self._random_increase)
        page.decrease_requested.connect(self._random_decrease)
        page.reset_requested.connect(self._random_reset)
        page.shiny_requested.connect(self._random_shiny)
        return page

    def _create_element_page(self) -> ElementPage:
        page = ElementPage()
        page.increase_requested.connect(self._element_increase)
        page.decrease_requested.connect(self._element_decrease)
        page.reset_requested.connect(self._element_reset)
        page.shiny_requested.connect(self._element_shiny)
        return page

    def _create_shiny_page(self) -> ShinyPage:
        page = ShinyPage()
        page.manual_add_requested.connect(self._manual_add_shiny)
        page.delete_requested.connect(self._delete_shiny)
        return page

    def _create_settings_page(self) -> SettingsPage:
        page = SettingsPage()
        page.theme_toggle_requested.connect(self._toggle_theme)
        page.update_check_requested.connect(self._check_for_updates)
        page.github_requested.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_PROJECT_URL)))
        page.content_import_requested.connect(self._import_content_pack)
        page.content_open_requested.connect(self._open_content_directory)
        page.content_rollback_requested.connect(self._rollback_content_pack)
        page.set_theme_name(self._settings_svc.theme)
        self._update_content_controls(page)
        return page

    def _refresh_page(self, index: int, slot: SaveSlot) -> None:
        page = self._pages.get(index)
        if index == PAGE_FAMILY and isinstance(page, FamilyPage):
            selection = self._family_selections.get(slot.name, {})
            page.load_slot(slot, selection if isinstance(selection, dict) else {})
        elif index == PAGE_RANDOM and isinstance(page, RandomPage):
            page.load_slot(slot)
        elif index == PAGE_ELEMENT and isinstance(page, ElementPage):
            page.load_slot(slot)
        elif index == PAGE_SHINY and isinstance(page, ShinyPage):
            page.load_slot(slot)

    def _refresh_built_pages(self, slot: SaveSlot) -> None:
        for index in sorted(self._pages):
            self._refresh_page(index, slot)
        self.activity_drawer.set_logs(slot.logs)
        self._update_random_quick(slot.random_pool)

    def _capture_family_selection(self) -> None:
        slot = self._save_svc.current
        page = self._pages.get(PAGE_FAMILY)
        if slot and isinstance(page, FamilyPage):
            self._family_selections[slot.name] = page.selection_state()

    def _switch_save(self, name: str) -> None:
        if self._save_svc.current_name and self._save_svc.current_name != name:
            self._capture_family_selection()
        try:
            slot = self._save_svc.load_save(name)
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
            return
        self._refresh_built_pages(slot)
        self._refresh_save_combo()

    def _refresh_save_combo(self) -> None:
        current = self._save_svc.current_name or ""
        self.save_combo.blockSignals(True)
        self.save_combo.clear()
        self.save_combo.addItems(self._save_svc.list_saves())
        if current:
            self.save_combo.setCurrentText(current)
        self.save_combo.blockSignals(False)

    def _on_save_selected(self, name: str) -> None:
        if name and name != self._save_svc.current_name:
            self._switch_save(name)

    def _create_save(self) -> None:
        name, accepted = QInputDialog.getText(self, "新建存档", "存档名称")
        if not accepted or not name.strip():
            return
        self._capture_family_selection()
        try:
            slot = self._save_svc.create_save(name.strip())
            beep()
            self._refresh_save_combo()
            self._refresh_built_pages(slot)
        except Exception as exc:
            QMessageBox.critical(self, "创建失败", str(exc))

    def _rename_save(self) -> None:
        old_name = self._save_svc.current_name
        if not old_name:
            return
        new_name, accepted = QInputDialog.getText(self, "重命名存档", "新名称", text=old_name)
        if not accepted or not new_name.strip() or new_name.strip() == old_name:
            return
        self._capture_family_selection()
        try:
            self._save_svc.rename_save(old_name, new_name.strip())
            if old_name in self._family_selections:
                self._family_selections[new_name.strip()] = self._family_selections.pop(old_name)
            self._save_svc.save_current()
            beep()
            self._refresh_save_combo()
        except Exception as exc:
            QMessageBox.critical(self, "重命名失败", str(exc))

    def _delete_save(self) -> None:
        name = self._save_svc.current_name
        if not name:
            return
        if len(self._save_svc.list_saves()) <= 1:
            QMessageBox.warning(self, "无法删除", "至少需要保留一个存档。")
            return
        if not self._confirm(f"确定删除存档「{name}」吗？"):
            return
        try:
            self._save_svc.delete_save(name)
            self._family_selections.pop(name, None)
            saves = self._save_svc.list_saves()
            if saves:
                self._switch_save(saves[0])
            beep()
        except Exception as exc:
            QMessageBox.critical(self, "删除失败", str(exc))

    def _import_save(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入存档", "", "JSON 文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            slot = self._save_svc.import_save(path)
            self._refresh_save_combo()
            self._refresh_built_pages(slot)
            beep()
            QMessageBox.information(self, "导入成功", f"已导入存档「{slot.name}」。")
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def _export_save(self) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出存档", f"{slot.name}.json", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            self._save_svc.export_save(path)
            beep()
            QMessageBox.information(self, "导出成功", f"已导出至：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _after_operation(self, logs: list[ActivityLog]) -> None:
        if not logs:
            return
        self._save_svc.save_current()
        self.activity_drawer.prepend_logs(logs)
        slot = self._save_svc.current
        if slot:
            self._update_random_quick(slot.random_pool)

    def _family_increase(self, name: str) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        self._after_operation(slot.family_increase(name))
        page = self._pages.get(PAGE_FAMILY)
        if isinstance(page, FamilyPage):
            page.update_count(name, slot.family_pool.get(name, 0))

    def _family_decrease(self, name: str) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        self._after_operation(slot.family_decrease(name))
        page = self._pages.get(PAGE_FAMILY)
        if isinstance(page, FamilyPage):
            page.update_count(name, slot.family_pool.get(name, 0))

    def _family_reset(self, name: str) -> None:
        slot = self._save_svc.current
        if slot and self._confirm(f"确定重置「{name}」吗？"):
            self._after_operation(slot.family_reset(name))
            page = self._pages.get(PAGE_FAMILY)
            if isinstance(page, FamilyPage):
                page.update_count(name, slot.family_pool.get(name, 0))

    def _family_shiny(self, name: str, season: str) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        count = slot.family_pool.get(name, 0)
        if not self._can_record_shiny(count, name):
            return
        dialog = ShinyChoiceDialog(self, POOL_FAMILY, count, fixed_spirit=name, fixed_season=season)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _random_increase(self, name: str) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        self._after_operation(slot.random_increase(name))
        page = self._pages.get(PAGE_RANDOM)
        if isinstance(page, RandomPage):
            page.update_count(slot.random_pool)

    def _random_decrease(self) -> None:
        slot = self._save_svc.current
        if slot:
            beep()
            self._after_operation(slot.random_decrease())
            page = self._pages.get(PAGE_RANDOM)
            if isinstance(page, RandomPage):
                page.update_count(slot.random_pool)

    def _random_reset(self) -> None:
        slot = self._save_svc.current
        if slot and self._confirm("确定重置随机池吗？"):
            self._after_operation(slot.random_reset())
            page = self._pages.get(PAGE_RANDOM)
            if isinstance(page, RandomPage):
                page.update_count(slot.random_pool)

    def _random_shiny(self) -> None:
        slot = self._save_svc.current
        if not slot or not self._can_record_shiny(slot.random_pool, "随机池"):
            return
        dialog = ShinyChoiceDialog(self, POOL_RANDOM, slot.random_pool)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _element_increase(self, element: str) -> None:
        slot = self._save_svc.current
        if not slot or not element:
            return
        beep()
        self._after_operation(slot.element_increase(element))
        self._update_element_page(element, slot.element_pool.get(element, 0))

    def _element_decrease(self, element: str) -> None:
        slot = self._save_svc.current
        if not slot or not element:
            return
        beep()
        self._after_operation(slot.element_decrease(element))
        self._update_element_page(element, slot.element_pool.get(element, 0))

    def _element_reset(self, element: str) -> None:
        slot = self._save_svc.current
        if slot and element and self._confirm(f"确定重置「{element}」属性吗？"):
            self._after_operation(slot.element_reset(element))
            self._update_element_page(element, slot.element_pool.get(element, 0))

    def _element_shiny(self, element: str) -> None:
        slot = self._save_svc.current
        if not slot or not element:
            return
        count = slot.element_pool.get(element, 0)
        if not self._can_record_shiny(count, f"{element}属性"):
            return
        dialog = ShinyChoiceDialog(self, POOL_ELEMENT, count, element=element)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _update_element_page(self, element: str, count: int) -> None:
        page = self._pages.get(PAGE_ELEMENT)
        if isinstance(page, ElementPage):
            page.update_count(element, count)

    def _manual_add_shiny(self) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        dialog = ManualShinyDialog(self, slot)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _delete_shiny(self, index: int) -> None:
        slot = self._save_svc.current
        if not slot or not self._confirm("确定删除这条异色记录吗？"):
            return
        if slot.delete_shiny_record(index):
            self._save_svc.save_current()
            page = self._pages.get(PAGE_SHINY)
            if isinstance(page, ShinyPage):
                page.refresh()
            beep()

    def _apply_shiny_record(self, data: dict) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        pool_type = str(data.get("pool_type", POOL_UNKNOWN))
        spirit_name = str(data.get("spirit_name", ""))
        element = str(data.get("element", ""))
        reset_after = bool(data.get("reset_after_record", True))
        log = slot.add_shiny_record(
            pool_type=pool_type,
            spirit_name=spirit_name,
            pity_count=int(data.get("pity_count", 0)),
            season=str(data.get("season", "")),
            element=element,
            reset_after_record=reset_after,
        )
        if reset_after:
            if pool_type == POOL_RANDOM:
                slot.clear_random_pool()
            elif pool_type == POOL_FAMILY:
                slot.clear_family_pool(spirit_name)
            elif pool_type == POOL_ELEMENT:
                slot.clear_element_pool(element)
        self._after_operation([log])
        if pool_type == POOL_RANDOM:
            page = self._pages.get(PAGE_RANDOM)
            if isinstance(page, RandomPage):
                page.update_count(slot.random_pool)
        elif pool_type == POOL_FAMILY:
            page = self._pages.get(PAGE_FAMILY)
            if isinstance(page, FamilyPage):
                page.update_count(spirit_name, slot.family_pool.get(spirit_name, 0))
        elif pool_type == POOL_ELEMENT:
            self._update_element_page(element, slot.element_pool.get(element, 0))
        shiny_page = self._pages.get(PAGE_SHINY)
        if isinstance(shiny_page, ShinyPage):
            shiny_page.refresh()
        beep()

    def _can_record_shiny(self, count: int, target: str) -> bool:
        if count > 0:
            return True
        QMessageBox.warning(self, "无法记录异色", f"「{target}」当前保底为 0。")
        return False

    def _confirm(self, message: str) -> bool:
        return QMessageBox.question(self, "确认", message) == QMessageBox.StandardButton.Yes

    def _update_random_quick(self, count: int) -> None:
        self.random_quick_btn.setText(f"随机池  {count}")

    def _set_activity_visible(self, visible: bool) -> None:
        self._position_activity_drawer()
        self.activity_drawer.setVisible(bool(visible))
        if visible:
            self.activity_drawer.raise_()
        self.activity_btn.setChecked(bool(visible))

    def _position_activity_drawer(self) -> None:
        if not hasattr(self, "activity_drawer"):
            return
        root = self.centralWidget()
        if root is None:
            return
        top_height = self._top_bar.height() if hasattr(self, "_top_bar") else 0
        width = self.activity_drawer.width()
        self.activity_drawer.setGeometry(
            max(0, root.width() - width),
            top_height,
            width,
            max(0, root.height() - top_height),
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_activity_drawer()

    def _toggle_theme(self) -> None:
        theme = self._settings_svc.toggle_theme()
        app = QApplication.instance()
        if app:
            apply_theme(app, theme)
        self._update_theme_controls()
        for page in self._pages.values():
            page.update()

    def _update_theme_controls(self) -> None:
        self.theme_btn.setText("浅色主题" if self._settings_svc.theme == THEME_DARK else "深色主题")
        page = self._pages.get(PAGE_SETTINGS)
        if isinstance(page, SettingsPage):
            page.set_theme_name(self._settings_svc.theme)

    def _update_content_controls(self, page: SettingsPage | None = None) -> None:
        target = page or self._pages.get(PAGE_SETTINGS)
        if not isinstance(target, SettingsPage):
            return
        if self._content_svc is None:
            target.set_content_state("当前运行环境未配置本地资源目录。", False, False)
            return
        target.set_content_state(
            self._content_svc.summary(),
            self._content_svc.can_rollback(),
        )

    def _import_content_pack(self) -> None:
        if self._content_svc is None:
            return
        archive_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "导入赛季资源包",
            str(Path.home()),
            "赛季资源包 (*.zip)",
        )
        if not archive_path:
            return
        try:
            result = self._content_svc.install_pack(archive_path)
        except (ContentPackError, OSError) as exc:
            QMessageBox.critical(self, "资源包导入失败", str(exc))
            return
        self._update_content_controls()
        if result.activated:
            message = (
                f"已安装并启用 {result.season} v{result.pack_version}。\n\n"
                "资源将在下次启动时完整生效。"
            )
        else:
            message = f"{result.season} v{result.pack_version} 已安装且当前正在使用。"
        QMessageBox.information(self, "资源包导入完成", message)

    def _open_content_directory(self) -> None:
        if self._content_svc is None:
            return
        directory = self._content_svc.ensure_content_root()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _rollback_content_pack(self) -> None:
        if self._content_svc is None or not self._content_svc.can_rollback():
            return
        if not self._confirm("确定回滚到上一次资源配置吗？"):
            return
        try:
            result = self._content_svc.rollback()
        except (ContentPackError, OSError) as exc:
            QMessageBox.critical(self, "资源回滚失败", str(exc))
            return
        self._update_content_controls()
        active = "、".join(result.active_seasons) if result.active_seasons else "仅内置资源"
        QMessageBox.information(
            self,
            "资源回滚完成",
            f"已恢复为：{active}\n\n资源将在下次启动时完整生效。",
        )

    def _network_api(self):
        if self._network_module is None:
            from PySide6 import QtNetwork

            self._network_module = QtNetwork
            self._network_manager = QtNetwork.QNetworkAccessManager(self)
        return self._network_module

    def _check_for_updates(self) -> None:
        if self._update_reply is not None:
            return
        page = self._pages.get(PAGE_SETTINGS)
        if isinstance(page, SettingsPage):
            page.set_update_checking(True)
            page.update_status.setText("正在连接版本检查源…")
        network = self._network_api()
        request = network.QNetworkRequest(QUrl(UPDATE_MANIFEST_URL))
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"User-Agent", f"{APP_NAME}/{APP_VERSION}".encode("utf-8"))
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(10000)
        self._update_reply = self._network_manager.get(request)
        self._update_reply.finished.connect(self._on_update_finished)

    def _on_update_finished(self) -> None:
        reply = self._update_reply
        self._update_reply = None
        page = self._pages.get(PAGE_SETTINGS)
        if isinstance(page, SettingsPage):
            page.set_update_checking(False)
        if reply is None:
            return
        network = self._network_api()
        try:
            if reply.error() != network.QNetworkReply.NetworkError.NoError:
                raise RuntimeError(reply.errorString())
            payload = bytes(reply.readAll()).decode("utf-8", errors="replace")
            data = json.loads(payload)
            version = str(data.get("tag_name") or data.get("version") or "").strip()
            if not version:
                raise ValueError("版本清单中没有版本号。")
            if not version.lower().startswith("v"):
                version = f"v{version}"
            if is_newer_version(version, APP_VERSION):
                if isinstance(page, SettingsPage):
                    page.update_status.setText(f"发现新版本 {version}")
                if QMessageBox.question(self, "发现新版本", f"发现新版本 {version}，是否打开下载页面？") == QMessageBox.StandardButton.Yes:
                    open_url = str(data.get("download_url") or data.get("release_url") or GITHUB_RELEASES_URL)
                    QDesktopServices.openUrl(QUrl(open_url))
            else:
                if isinstance(page, SettingsPage):
                    page.update_status.setText(f"当前已是最新版本 v{APP_VERSION}")
                QMessageBox.information(self, "检查更新", f"当前已是最新版本：v{APP_VERSION}")
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(page, SettingsPage):
                page.update_status.setText("检查失败，请稍后重试")
            if QMessageBox.question(self, "检查更新失败", f"{exc}\n\n是否打开 Releases 页面？") == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL))
        finally:
            reply.deleteLater()

    def _persist_ui_state(self) -> None:
        self._capture_family_selection()
        self._settings_svc.set_ui_state({
            "family_selections": self._family_selections,
        })

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_ui_state()
        super().closeEvent(event)

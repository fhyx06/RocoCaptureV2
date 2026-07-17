from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.content.repository import BUILTIN_CONTENT_ROOT, ContentRepository
from src.models.constants import ELEMENTS, POOL_FAMILY, POOL_RANDOM
from src.qt_ui_v2.main_window import (
    PAGE_COUNT,
    PAGE_ELEMENT,
    PAGE_FAMILY,
    PAGE_RANDOM,
    PAGE_SETTINGS,
    PAGE_SHINY,
    QtMainWindowV2,
)
from src.qt_ui_v2.pages.family_page import FamilyPage
from src.qt_ui_v2.pages.shiny_page import ShinyPage
from src.qt_ui_v2.models import SHINY_INDEX_ROLE, SHINY_RECORD_ROLE
from src.qt_ui_v2.theme import apply_theme, configure_font
from src.services.save_service import SaveService
from src.services.content_pack_service import ContentPackService
from src.services.settings_service import SettingsService


class UiV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        configure_font(cls.app)

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_service = SaveService(self.temp_dir.name)
        self.slot = self.save_service.create_save("a")
        self.family_name = next(iter(self.slot.family_pool))
        self.settings = SettingsService(os.path.join(self.temp_dir.name, "settings.json"))
        self.content_repository = ContentRepository(
            BUILTIN_CONTENT_ROOT,
            os.path.join(self.temp_dir.name, "content"),
        )
        self.content_service = ContentPackService(
            self.content_repository,
            os.path.join(self.temp_dir.name, "content"),
        )
        apply_theme(self.app, self.settings.theme)
        self.window = QtMainWindowV2(self.save_service, self.settings, self.content_service)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def test_family_is_default_and_other_pages_are_lazy(self) -> None:
        self.assertEqual(self.window._current_page, PAGE_FAMILY)
        self.assertEqual(set(self.window._pages), {PAGE_FAMILY})
        self.assertEqual(self.window.page_stack.count(), PAGE_COUNT)
        family = self.window._pages[PAGE_FAMILY]
        self.assertIsInstance(family, FamilyPage)
        self.assertGreater(family.model.rowCount(), 0)

    def test_all_pages_can_be_created_on_demand(self) -> None:
        for index in (PAGE_RANDOM, PAGE_ELEMENT, PAGE_SHINY, PAGE_SETTINGS):
            self.window._set_page(index)
            self.app.processEvents()
            self.assertIn(index, self.window._pages)
            self.assertEqual(self.window.page_stack.currentIndex(), index)
        self.assertEqual(len(self.window._pages), PAGE_COUNT)

    def test_family_operation_updates_model_and_activity_without_rebuild(self) -> None:
        page = self.window._pages[PAGE_FAMILY]
        page_id = id(page)
        with patch("src.qt_ui_v2.main_window.beep"):
            self.window._family_increase(self.family_name)

        self.assertEqual(self.save_service.current.family_pool[self.family_name], 1)
        self.assertEqual(page.model.item(page.model.find_row(self.family_name))["count"], 1)
        self.assertEqual(self.window.activity_drawer.source_model.rowCount(), 1)
        self.assertEqual(id(self.window._pages[PAGE_FAMILY]), page_id)

    def test_family_detail_uses_large_hero_art(self) -> None:
        page = self.window._pages[PAGE_FAMILY]
        pixmap = page.detail_icon.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertGreaterEqual(page.detail_icon.minimumHeight(), 180)
        self.assertGreaterEqual(pixmap.width(), 150)
        self.assertGreaterEqual(pixmap.height(), 150)

    def test_family_detail_uses_element_icons_instead_of_text_badges(self) -> None:
        page = self.window._pages[PAGE_FAMILY]
        item = page._selected_item()
        self.assertIsNotNone(item)
        elements = item["elements"]

        for index, element in enumerate(elements):
            badge = page.element_badges[index]
            self.assertEqual(badge.text(), "")
            self.assertIsNotNone(badge.pixmap())
            self.assertFalse(badge.pixmap().isNull())
            self.assertEqual(badge.toolTip(), f"{element}属性")

    def test_element_page_uses_all_elements_and_updates_incrementally(self) -> None:
        self.window._set_page(PAGE_ELEMENT)
        self.app.processEvents()
        page = self.window._pages[PAGE_ELEMENT]
        self.assertEqual(set(page._buttons), set(ELEMENTS))
        element = ELEMENTS[0]
        page.select_element(element)
        with patch("src.qt_ui_v2.main_window.beep"):
            self.window._element_increase(element)
        self.assertIn("保底 1", page._buttons[element].text())

    def test_activity_drawer_is_hidden_by_default_and_toggleable(self) -> None:
        self.assertFalse(self.window.activity_drawer.isVisible())
        self.window._set_activity_visible(True)
        self.app.processEvents()
        self.assertTrue(self.window.activity_drawer.isVisible())
        self.assertTrue(self.window.activity_btn.isChecked())

    def test_shiny_records_use_responsive_cards_and_filters(self) -> None:
        slot = self.save_service.current
        self.assertIsNotNone(slot)
        slot.add_shiny_record(
            POOL_FAMILY,
            self.family_name,
            42,
            season="S1",
            element="火",
            reset_after_record=False,
        )
        slot.add_shiny_record(
            POOL_RANDOM,
            self.family_name,
            7,
            season="S2",
            reset_after_record=False,
        )
        self.window._set_page(PAGE_SHINY)
        self.app.processEvents()
        page = self.window._pages[PAGE_SHINY]
        self.assertIsInstance(page, ShinyPage)
        self.assertEqual(page.model.record_count(), 2)
        self.assertEqual(page.record_stack.currentWidget(), page.gallery)
        self.assertIsNotNone(page.model.index(0, 0).data(SHINY_RECORD_ROLE))
        self.assertEqual(page._columns, 2)

        page.gallery.setCurrentIndex(page.model.index(0, 1))
        self.app.processEvents()
        self.assertTrue(page.delete_btn.isEnabled())
        self.assertEqual(page.model.index(0, 1).data(SHINY_INDEX_ROLE), 0)

        page.gallery.setFixedWidth(650)
        self.app.processEvents()
        page._relayout()
        self.assertEqual(page._columns, 1)

        page.pool_combo.setCurrentIndex(page.pool_combo.findData(POOL_FAMILY))
        self.app.processEvents()
        self.assertEqual(page.model.record_count(), 1)
        self.assertEqual(page.result_summary.text(), "1 条记录")

    def test_ui_state_preserves_family_selection_shape(self) -> None:
        self.window._persist_ui_state()
        state = self.settings.ui_state()
        self.assertIn("a", state["family_selections"])
        self.assertIn("season", state["family_selections"]["a"])

    def test_settings_exposes_local_content_pack_controls(self) -> None:
        self.window._set_page(PAGE_SETTINGS)
        self.app.processEvents()
        page = self.window._pages[PAGE_SETTINGS]
        self.assertIn("内置资源", page.content_status.text())
        self.assertTrue(page.content_import_btn.isEnabled())
        self.assertTrue(page.content_open_btn.isEnabled())
        self.assertFalse(page.content_rollback_btn.isEnabled())

    def test_family_remains_start_page_after_visiting_settings(self) -> None:
        self.window._set_page(PAGE_SETTINGS)
        self.window._persist_ui_state()
        self.window.close()
        restored = QtMainWindowV2(self.save_service, self.settings, self.content_service)
        try:
            self.assertEqual(restored._current_page, PAGE_FAMILY)
            self.assertEqual(set(restored._pages), {PAGE_FAMILY})
        finally:
            restored.close()


if __name__ == "__main__":
    unittest.main()

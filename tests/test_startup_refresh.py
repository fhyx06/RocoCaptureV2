from __future__ import annotations

import os
import tempfile
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.qt_ui.main_window import (
    LOG_DISPLAY_LIMIT,
    PAGE_COUNT,
    PAGE_ELEMENT,
    PAGE_FAMILY,
    PAGE_RANDOM,
    PAGE_SETTINGS,
    PAGE_SHINY,
    QtMainWindow,
    _spirit_icon_index,
    spirit_icon,
)
from src.services.save_service import SaveService
from src.services.settings_service import SettingsService


class StartupRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_service = SaveService(self.temp_dir.name)

        first = self.save_service.create_save("a")
        self.family_name = next(iter(first.family_pool))
        first.family_increase(self.family_name)
        first.element_increase("火")
        self.save_service.save_current()

        second = self.save_service.create_save("b")
        second.family_increase(self.family_name)
        second.family_increase(self.family_name)
        second.element_increase("火")
        second.element_increase("火")
        self.save_service.save_current()

        settings = SettingsService(os.path.join(self.temp_dir.name, "settings.json"))
        self.window = QtMainWindow(self.save_service, settings)

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def test_startup_only_builds_first_page(self) -> None:
        self.assertEqual(self.window._built_pages, {PAGE_RANDOM})
        self.assertEqual(self.window.page_stack.count(), PAGE_COUNT)
        self.assertIsNone(self.window._network_module)

    def test_pages_are_built_on_first_visit(self) -> None:
        for index in (PAGE_FAMILY, PAGE_ELEMENT, PAGE_SHINY, PAGE_SETTINGS):
            self.window.sidebar.setCurrentRow(index)
            self.app.processEvents()
            self.assertIn(index, self.window._built_pages)
            self.assertEqual(self.window.page_stack.currentIndex(), index)
        self.assertEqual(len(self.window._built_pages), PAGE_COUNT)
        self.assertIsNone(self.window._network_module)

    def test_save_switch_reuses_family_and_element_widgets(self) -> None:
        self.window.sidebar.setCurrentRow(PAGE_FAMILY)
        self.window.sidebar.setCurrentRow(PAGE_ELEMENT)
        self.app.processEvents()

        family_label = self.window._family_count_labels[self.family_name][0]
        element_button = self.window._element_items["火"]
        self.window._switch_save("b")
        self.app.processEvents()

        self.assertIs(self.window._family_count_labels[self.family_name][0], family_label)
        self.assertIs(self.window._element_items["火"], element_button)
        self.assertEqual(family_label.text(), "2")
        self.assertIn("保底 2", element_button.text())

    def test_log_panel_limits_rendered_history_without_deleting_data(self) -> None:
        slot = self.save_service.current
        assert slot is not None
        for _ in range(LOG_DISPLAY_LIMIT + 5):
            slot.random_increase()
        self.window._load_logs(slot.logs)

        self.assertIn(f"仅显示最近 {LOG_DISPLAY_LIMIT} 条", self.window.log_text.toPlainText())
        self.assertGreater(len(slot.logs), LOG_DISPLAY_LIMIT)

    def test_spirit_icon_lookup_is_cached(self) -> None:
        spirit_icon.cache_clear()
        _spirit_icon_index.cache_clear()
        first = spirit_icon(self.family_name, "S1")
        second = spirit_icon(self.family_name, "S1")

        self.assertFalse(first.isNull())
        self.assertIs(first, second)
        self.assertGreaterEqual(spirit_icon.cache_info().hits, 1)


if __name__ == "__main__":
    unittest.main()

"""Minimal PySide6 offscreen UI gate for basic/advanced visibility.

No network, keyring, Huawei API or radio writes.
"""

import os
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from pocket_manager.qt_app import PocketWindow


class BasicAdvancedViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        with patch("pocket_manager.qt_app.ProfileStore") as factory:
            factory.return_value.list.return_value = []
            self.window = PocketWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_simple_mode_shows_main_tasks_hides_technical_panels(self):
        tabs = self.window.tabs
        self.assertEqual(tabs.tabText(0), "Stato connessione")
        self.assertEqual(tabs.tabText(1), "Andamento")
        self.assertEqual(tabs.tabText(3), "Confronta bande")
        self.assertTrue(tabs.isTabVisible(0))
        self.assertTrue(tabs.isTabVisible(1))
        self.assertTrue(tabs.isTabVisible(3))
        self.assertFalse(tabs.isTabVisible(2))
        self.assertFalse(tabs.isTabVisible(4))
        self.assertFalse(self.window.host.isVisible())
        self.assertFalse(self.window.signals.isVisible())
        self.assertFalse(self.window.log.isVisible())
        self.assertTrue(self.window.benchmark_btn.isVisible())

    def test_advanced_toggle_keeps_radio_and_diagnostic_controls(self):
        self.window.advanced_toggle.setChecked(True)
        self.app.processEvents()
        self.assertTrue(self.window.tabs.isTabVisible(2))
        self.assertTrue(self.window.tabs.isTabVisible(4))
        self.assertTrue(self.window.host.isVisible())
        self.assertTrue(self.window.signals.isVisible())
        self.assertTrue(self.window.log.isVisible())
        self.assertTrue(self.window.apply_btn.isEnabled() is False)
        self.assertIn("RSRP", [
            self.window.scan_table.horizontalHeaderItem(i).text()
            for i in range(self.window.scan_table.columnCount())
        ])
        self.window.tabs.setCurrentIndex(4)
        self.window.advanced_toggle.setChecked(False)
        self.app.processEvents()
        self.assertEqual(self.window.tabs.currentIndex(), 0)
        self.assertFalse(self.window.tabs.isTabVisible(4))

    def test_benchmark_labels_explain_latency_without_jargon(self):
        headers = [
            self.window.benchmark_table.horizontalHeaderItem(i).text()
            for i in range(self.window.benchmark_table.columnCount())
        ]
        self.assertIn("Tempo di risposta (ms)", headers)
        self.assertTrue(
            "TTFB" in self.window.benchmark_table.horizontalHeaderItem(3).toolTip()
        )
        self.assertNotIn("TTFB", " ".join(headers))
        self.assertEqual(self.window.benchmark_btn.text(), "2. Avvia confronto")


if __name__ == "__main__":
    unittest.main()

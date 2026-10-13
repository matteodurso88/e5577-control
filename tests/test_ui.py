"""Minimal PySide6 offscreen UI gate for basic/advanced visibility.

No network, keyring, Huawei API or radio writes.
"""

import os
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication
from shiboken6 import delete as delete_qt_object

from pocket_manager.qt_app import PocketWindow


class BasicAdvancedViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        existing = QApplication.instance()
        cls._owns_app = existing is None
        cls.app = existing if existing is not None else QApplication([])

    @classmethod
    def tearDownClass(cls):
        # Dispose of the Qt application before Python module finalization.
        # Otherwise some PySide6/offscreen versions can segfault *after*
        # unittest has already printed its summary.
        if cls._owns_app:
            cls.app.quit()
            cls.app.processEvents()
            delete_qt_object(cls.app)
        cls.app = None

    def setUp(self):
        with patch("pocket_manager.qt_app.ProfileStore") as factory:
            factory.return_value.list.return_value = []
            self.window = PocketWindow()
        # Keep QWidget visible to the test, without mapping a native window.
        # This exercises Qt visibility and tabs without the offscreen renderer.
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.window = None

    def test_simple_mode_shows_main_tasks_hides_technical_panels(self):
        tabs = self.window.tabs
        self.assertEqual(tabs.tabText(0), "Stato connessione")
        self.assertEqual(tabs.tabText(1), "Andamento")
        self.assertEqual(tabs.tabText(2), "Messaggi")
        self.assertEqual(tabs.tabText(4), "Confronta bande")
        self.assertTrue(tabs.isTabVisible(0))
        self.assertTrue(tabs.isTabVisible(1))
        self.assertTrue(tabs.isTabVisible(2))
        self.assertTrue(tabs.isTabVisible(4))
        self.assertFalse(tabs.isTabVisible(3))
        self.assertFalse(tabs.isTabVisible(5))
        self.assertFalse(self.window.host.isVisible())
        self.assertFalse(self.window.signals.isVisible())
        self.assertFalse(self.window.log.isVisible())
        # A child of a non-selected tab is not isVisible() in Qt, even
        # when that tab is enabled and available. Select the tab first.
        tabs.setCurrentIndex(4)
        self.app.processEvents()
        self.assertTrue(self.window.benchmark_btn.isVisible())
        tabs.setCurrentIndex(0)

    def test_advanced_toggle_keeps_radio_and_diagnostic_controls(self):
        self.window.advanced_toggle.setChecked(True)
        self.app.processEvents()
        self.assertTrue(self.window.tabs.isTabVisible(3))
        self.assertTrue(self.window.tabs.isTabVisible(5))
        self.assertTrue(self.window.host.isVisible())
        self.assertTrue(self.window.signals.isVisible())
        self.assertTrue(self.window.log.isVisible())
        self.assertTrue(self.window.apply_btn.isEnabled() is False)
        self.assertIn("RSRP", [
            self.window.scan_table.horizontalHeaderItem(i).text()
            for i in range(self.window.scan_table.columnCount())
        ])
        self.window.tabs.setCurrentIndex(5)
        self.window.advanced_toggle.setChecked(False)
        self.app.processEvents()
        self.assertEqual(self.window.tabs.currentIndex(), 0)
        self.assertFalse(self.window.tabs.isTabVisible(5))

    def test_dashboard_cards_show_deduced_b7_and_firmware_signal_bar(self):
        payload = {
            "net_mode": {"LTEBand": "40", "NetworkMode": "00"},
            "monitoring_status": {
                "ConnectionStatus": "901", "CurrentNetworkType": "19",
                "SignalIcon": "1", "maxsignal": "5", "SimStatus": "1",
            },
            "plmn": {"FullName": "WINDTRE", "Rat": "7"},
            "signal": {"lte_bandinfo": None, "rsrp": None, "sinr": None},
        }
        self.window._reading(payload)
        self.assertIn("4G LTE", self.window.network_value.text())
        self.assertIn("WINDTRE", self.window.network_hint.text())
        self.assertEqual(self.window.band_value.text(), "B7 · dedotta")
        self.assertIn("unica banda possibile", self.window.band_hint.text())
        self.assertEqual(self.window.signal_value.text(), "1 su 5 tacche")
        self.assertEqual(self.window.signal_gauge.value(), 1)
        self.assertEqual(self.window.signal_gauge.maximum(), 5)

    def test_dashboard_keeps_uncertainty_when_multiple_bands_are_allowed(self):
        self.window._reading({
            "net_mode": {"LTEBand": "800d5", "NetworkMode": "00"},
            "monitoring_status": {
                "ConnectionStatus": "901", "CurrentNetworkType": "19",
                "SignalIcon": "0", "maxsignal": "5",
            },
            "plmn": {"FullName": "WINDTRE", "Rat": "7"},
            "signal": {"lte_bandinfo": None},
        })
        self.assertEqual(self.window.band_value.text(), "Non rilevabile")
        self.assertIn("B1", self.window.band_hint.text())
        self.assertEqual(self.window.signal_gauge.value(), 0)

    def test_advanced_view_still_contains_unabridged_network_fields(self):
        self.window.advanced_toggle.setChecked(True)
        self.app.processEvents()
        self.assertTrue(self.window.advanced_network_group.isVisible())
        self.assertIn("connection", self.window.network_labels)
        self.assertIn("rf", self.window.network_labels)
        self.window.advanced_toggle.setChecked(False)
        self.app.processEvents()
        self.assertFalse(self.window.advanced_network_group.isVisible())
        self.assertTrue(self.window.band_value.isVisible())

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

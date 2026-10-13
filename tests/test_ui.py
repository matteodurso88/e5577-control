"""Minimal PySide6 offscreen UI gate for basic/advanced visibility.

No network, keyring, Huawei API or radio writes.
"""

import os
import unittest
from unittest.mock import patch, Mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import (QApplication, QMessageBox, QFrame,
                              QGroupBox, QTableWidget, QPlainTextEdit)
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
        # Detailed RF network information moved off Home into tab 5.
        self.window.tabs.setCurrentIndex(5)
        self.app.processEvents()
        self.assertTrue(self.window.advanced_network_group.isVisible())
        self.assertTrue(self.window.advanced_signal_group.isVisible())
        self.assertTrue(self.window.signals.isVisible())
        self.assertIn("connection", self.window.network_labels)
        self.assertIn("rf", self.window.network_labels)
        self.window.advanced_toggle.setChecked(False)
        self.app.processEvents()
        self.assertFalse(self.window.advanced_network_group.isVisible())
        self.assertEqual(self.window.tabs.currentIndex(), 0)
        self.assertTrue(self.window.band_value.isVisible())

    def test_home_contains_cards_only_and_mobile_controls_inside_network_card(self):
        home = self.window.tabs.widget(0)
        # All text in Home belongs to the cards (no loose diagnostic tables
        # or paragraphs below them). Detailed RF is in advanced tab 5.
        self.assertEqual(home.findChildren(QGroupBox), [])
        self.assertEqual(home.findChildren(QTableWidget), [])
        network_frame = self.window.traffic_label.parentWidget()
        self.assertIsInstance(network_frame, QFrame)
        self.assertEqual(network_frame.objectName(), "summaryCard")
        self.assertIs(self.window.data_toggle.parentWidget(), network_frame)
        self.assertIs(self.window.data_state.parentWidget(), network_frame)
        for field in (self.window.band_value, self.window.signal_value,
                      self.window.sms_value):
            self.assertEqual(field.parentWidget().objectName(), "summaryCard")
        self.window._reading({
            "monitoring_status": {"ConnectionStatus": "901",
                                  "CurrentNetworkType": "19"},
            "plmn": {"FullName": "WINDTRE", "Rat": "7"},
            "traffic_statistics": {"CurrentDownloadRate": "2048",
                                   "CurrentUploadRate": "1024"},
            "mobile_data": {"dataswitch": "1"},
        })
        self.assertIn("2.0 KiB/s", self.window.traffic_label.text())
        self.assertIn("1.0 KiB/s", self.window.traffic_label.text())

    def test_sms_double_click_opens_full_plain_text_message_dialog(self):
        from pocket_manager.device_features import SmsMessage

        body = "<script>non eseguire</script>\nSeconda riga di testo SMS."
        self.window._show_sms([
            SmsMessage("12", "<b>Mittente</b>", "2026-10-13 11:44",
                       body, False)
        ])
        reader = self.window._create_sms_reader(0)
        self.assertIsNotNone(reader)
        self.assertEqual(reader.windowTitle(), "Leggi SMS")
        editor = reader.findChild(QPlainTextEdit, "smsReaderBody")
        self.assertTrue(editor.isReadOnly())
        self.assertEqual(editor.toPlainText(), body)
        header = reader.findChild(type(self.window.status), "smsReaderHeader")
        self.assertEqual(header.textFormat(), Qt.TextFormat.PlainText)
        self.assertIn("<b>Mittente</b>", header.text())
        reader.close()
        reader.deleteLater()
        self.assertIsNone(self.window._create_sms_reader(25))

        # Confirm that Qt's actual double-click signal opens the reader,
        # without showing a blocking modal during headless tests.
        fake_dialog = Mock()
        with patch.object(self.window, "_create_sms_reader",
                          return_value=fake_dialog) as creator:
            self.window.sms_table.cellDoubleClicked.emit(0, 1)
            creator.assert_called_once_with(0)
            fake_dialog.exec.assert_called_once()
        self.assertNotIn("Seconda riga", self.window.raw.toPlainText())
        self.assertNotIn("Seconda riga", self.window.log.toPlainText())

    def test_sms_reader_closes_when_disconnecting(self):
        from pocket_manager.device_features import SmsMessage

        self.window._show_sms([
            SmsMessage("1", "test", "2026-10-13", "Test privato", True)
        ])
        fake_reader = Mock()
        self.window.sms_reader_dialog = fake_reader
        self.window._reset_sms()
        fake_reader.reject.assert_called_once()
        self.assertIsNone(self.window.sms_reader_dialog)
        self.assertEqual(self.window.messages, [])
        self.assertEqual(self.window.sms_table.rowCount(), 0)
        self.assertEqual(self.window.sms_text.toPlainText(), "")

    def test_diagnostics_split_keeps_radio_measurements_and_api_export(self):
        self.window.advanced_toggle.setChecked(True)
        self.window.tabs.setCurrentIndex(5)
        self.app.processEvents()
        diagnostics = self.window.tabs.widget(5)
        tab_groups = diagnostics.findChildren(type(self.window.tabs))
        self.assertEqual(len(tab_groups), 1)
        sections = tab_groups[0]
        self.assertEqual(sections.tabText(0), "Misure radio")
        self.assertEqual(sections.tabText(1), "API ed esportazione")
        self.assertTrue(self.window.advanced_signal_group.isVisible())
        sections.setCurrentIndex(1)
        self.app.processEvents()
        self.assertTrue(self.window.raw.isVisible())

    def test_sms_home_tile_and_inbox_are_plain_text(self):
        from pocket_manager.device_features import SmsMessage

        self.window._reading({
            "sms_count": {"LocalInbox": "5", "LocalUnread": "2"},
            "mobile_data": {"dataswitch": "1"},
        })
        self.assertEqual(self.window.sms_value.text(), "2 da leggere")
        self.assertIn("Ricevuti: 5", self.window.sms_hint.text())
        self.window._show_sms([
            SmsMessage("7", "+391111", "2026-10-13 10:30",
                       "<img src=x onerror=alert(1)> SMS test", True)
        ])
        self.window.tabs.setCurrentIndex(2)
        self.app.processEvents()
        self.assertEqual(self.window.sms_table.rowCount(), 1)
        self.assertIn("<img", self.window.sms_text.toPlainText())
        self.assertEqual(self.window.sms_text.toHtml().count("<img"), 0)
        self.assertNotIn("SMS test", self.window.raw.toPlainText())
        self.assertNotIn("SMS test", self.window.log.toPlainText())

    def test_mobile_toggle_requires_confirmation_and_never_changes_gui_login(self):
        self.window._reading({"mobile_data": {"dataswitch": "1"}})
        self.window.radio_worker = Mock()
        self.window._set_online(True)
        self.assertEqual(self.window.data_toggle.text(), "Disattiva dati mobili")
        with patch("pocket_manager.qt_app.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.No):
            self.window._toggle_mobile_data()
        self.window.radio_worker.submit.assert_not_called()
        with patch("pocket_manager.qt_app.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.Yes):
            self.window._toggle_mobile_data()
        self.window.radio_worker.submit.assert_called_once_with(
            "mobile_switch", enabled=False
        )
        self.assertTrue(self.window.busy)
        self.window.radio_worker = None
        self.window.busy = False

    def test_mobile_switch_unknown_state_is_disabled(self):
        self.window._reading({"mobile_data": {"__error__": "No support"}})
        self.window._set_online(True)
        self.assertFalse(self.window.data_toggle.isEnabled())
        self.assertEqual(self.window.data_toggle.text(), "Comando non disponibile")
        self.assertTrue(self.window.tabs.isTabVisible(2))

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

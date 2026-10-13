"""Read-only telemetry tests: no PySide6, network, or physical modem required."""

from datetime import datetime, timezone
import unittest

from pocket_manager.telemetry import (
    TelemetryTimeline, format_rate, traffic_rates,
)


class TrafficRatesTests(unittest.TestCase):
    def test_valid_huawei_rates_are_bytes_per_second(self):
        self.assertEqual(traffic_rates({
            "CurrentDownloadRate": "2048",
            "CurrentUploadRate": 0,
            "TotalDownload": "99999",
        }), (2048, 0))
        self.assertEqual(format_rate(2048), "2.0 KiB/s")
        self.assertEqual(format_rate(0), "0 B/s")
        self.assertEqual(format_rate(None), "—")

    def test_unsupported_or_malformed_is_not_zero(self):
        for payload in (None, {}, {"__error__": "100002"},
                        {"CurrentDownloadRate": "-1", "CurrentUploadRate": True},
                        {"CurrentDownloadRate": "5.5", "CurrentUploadRate": "invalid"}):
            self.assertEqual(traffic_rates(payload), (None, None))
        # Valid zero is distinct from not reported.
        self.assertEqual(traffic_rates({"CurrentDownloadRate": "0"}), (0, None))


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.history = TelemetryTimeline(limit=2)
        self.now = datetime(2026, 10, 13, 1, 0, 0, tzinfo=timezone.utc)
        self.snapshot = {
            "monitoring_status": {
                "ConnectionStatus": "901", "CurrentNetworkType": "19",
                "SimStatus": "1", "SignalIcon": "1", "maxsignal": "5",
                "Imei": "PRIVATE",
            },
            "plmn": {"FullName": "WINDTRE", "Numeric": "22288"},
            "signal": {"rsrp": None, "sinr": None, "pci": None},
            "traffic_statistics": {
                "CurrentDownloadRate": "1024", "CurrentUploadRate": "128",
                "TotalDownload": "999999",
            },
            "device_information": {
                "SerialNumber": "PRIVATE", "DeviceName": "E5577Cs-321",
            },
        }

    def test_real_e5577_empty_rf_and_valid_connected_traffic(self):
        first = self.history.observe(self.snapshot, now=self.now)
        self.assertEqual(first.connection, "Connessa (secondo firmware)")
        self.assertEqual(first.network, "4G LTE")
        self.assertEqual(first.bars, "1/5 tacche (indicatore firmware)")
        self.assertEqual(first.down_bps, 1024)
        self.assertEqual(first.up_bps, 128)
        self.assertEqual(first.change, "Inizio osservazione")
        self.assertIn("indisponibili", first.rf)

    def test_change_only_tracks_status_fields_not_secret_or_rate(self):
        self.history.observe(self.snapshot, now=self.now)
        updated = {**self.snapshot,
                   "monitoring_status": {**self.snapshot["monitoring_status"],
                                         "SignalIcon": "2"},
                   "traffic_statistics": {"CurrentDownloadRate": "3000",
                                          "CurrentUploadRate": "0"}}
        point = self.history.observe(updated, now=self.now)
        self.assertEqual(point.change, "bars")
        self.assertEqual(point.down_bps, 3000)

    def test_missing_endpoint_is_marked_unavailable(self):
        self.history.observe(self.snapshot, now=self.now)
        updated = {**self.snapshot, "traffic_statistics": {"__error__": "No support"}}
        point = self.history.observe(updated, now=self.now)
        self.assertIsNone(point.down_bps)
        self.assertIsNone(point.up_bps)

    def test_whitelist_excludes_identifiers_and_is_bounded(self):
        self.history.observe(self.snapshot, now=self.now)
        self.history.observe(self.snapshot, now=self.now)
        self.history.observe(self.snapshot, now=self.now)
        data = self.history.export()
        self.assertEqual(len(data), 2)
        text = str(data)
        for sensitive in ("PRIVATE", "SerialNumber", "Imei", "TotalDownload", "DeviceName", "Numeric"):
            self.assertNotIn(sensitive, text)
        self.history.clear()
        self.assertEqual(self.history.export(), [])

    def test_naive_datetime_and_bad_limit_are_rejected(self):
        with self.assertRaises(ValueError):
            TelemetryTimeline(0)
        with self.assertRaises(ValueError):
            self.history.observe(self.snapshot, now=datetime(2026, 10, 13))
        self.assertEqual(self.history.export(), [])


if __name__ == "__main__":
    unittest.main()

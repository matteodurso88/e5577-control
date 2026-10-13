"""Pure radio + mocked Huawei interface tests (never touches a modem)."""

import threading
import unittest
from unittest.mock import patch

from pocket_manager.backend import HuaweiRadioBackend, RadioError
from pocket_manager.radio import (
    RadioConfig, bands_from_mask, mask_hex, normalized_mask,
    numeric_metric, parse_mask, safe_json_data, supported_bands,
    has_radio_measurements,
)


class MasksTest(unittest.TestCase):
    def test_masks_match_legacy_script(self):
        self.assertEqual(mask_hex((1, 3, 7)), "45")
        self.assertEqual(mask_hex((3, 7)), "44")
        self.assertEqual(mask_hex((20,)), "80000")
        self.assertEqual(mask_hex((1, 3, 5, 7, 8, 20)), "800d5")
        self.assertEqual(bands_from_mask("800D5"), (1, 3, 5, 7, 8, 20))

    def test_hex_semantics(self):
        self.assertEqual(parse_mask("40"), 64)
        self.assertEqual(normalized_mask("00040"), "40")
        for invalid in ("gh", "", "-1"):
            with self.assertRaises(ValueError):
                parse_mask(invalid)
        with self.assertRaises(ValueError):
            mask_hex([])

    def test_api_capabilities_ignore_all_sentinel(self):
        payload = {"LTEBandList": {"LTEBand": [
            {"Value": "7FFFFFFFFFFFFFFF"}, {"Value": "1"},
            {"Value": "40"}, {"Value": "80000"},
        ]}}
        self.assertEqual(supported_bands(payload), (1, 7, 20))

    def test_no_capabilities_is_not_all_bands(self):
        self.assertEqual(supported_bands({}), ())

    def test_blank_firmware_signal_is_not_lte_measurement(self):
        signal = {"mode": "7", "psatt": "1", "rsrp": "", "rsrq": "",
                  "sinr": "", "rssi": "", "pci": ""}
        self.assertFalse(has_radio_measurements(signal))
        self.assertFalse(has_radio_measurements({}))
        self.assertFalse(has_radio_measurements({"__error__": "unavailable"}))
        self.assertTrue(has_radio_measurements({**signal, "rsrp": "-90dBm"}))

    def test_stats_and_redaction(self):
        self.assertEqual(numeric_metric("−91 dBm"), -91.0)
        self.assertEqual(numeric_metric("12.5 dB"), 12.5)
        self.assertIsNone(numeric_metric("—"))
        payload = {"RSRP": "-95", "imei": "hidden", "Token": "secret",
                   "nested": {"pci": 100, "macAddress": "hidden"}}
        self.assertEqual(safe_json_data(payload), {"RSRP": "-95", "nested": {"pci": 100}})


class FakeNet:
    def __init__(self):
        self.current = {"LTEBand": "800d5", "NetworkBand": "3fffffff", "NetworkMode": "03"}
        self.writes = []
        self.reject = False

    def net_mode(self):
        return dict(self.current)

    def set_net_mode(self, *, lteband, networkband, networkmode):
        if self.reject:
            raise RuntimeError("100003")
        self.writes.append((lteband, networkband, networkmode))
        self.current = {"LTEBand": lteband, "NetworkBand": networkband, "NetworkMode": networkmode}


class FakeDevice:
    def signal(self):
        return {"rsrp": "-100dBm", "rsrq": "-10dB", "sinr": "12dB",
                "rssi": "-75dBm", "pci": "17", "cellid": "101"}


class FakeClient:
    def __init__(self):
        self.net = FakeNet()
        self.device = FakeDevice()


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = HuaweiRadioBackend("192.168.8.1", "admin", "test")
        self.backend.client = FakeClient()

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_apply_readback_restore(self):
        updated = self.backend.apply("45", "03")
        self.assertEqual(updated.lte_band, "45")
        self.assertEqual(self.backend.previous.lte_band, "800d5")
        self.assertEqual(self.backend.client.net.writes, [("45", "3fffffff", "03")])
        restored = self.backend.restore()
        self.assertEqual(restored.lte_band, "800d5")

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_firmware_rejection_preserves_baseline(self):
        self.backend.client.net.reject = True
        with self.assertRaisesRegex(RadioError, "100003"):
            self.backend.apply("40", "03")
        self.assertEqual(self.backend.previous.lte_band, "800d5")

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_scan_restores_baseline(self):
        results = self.backend.scan([3, 7], threading.Event(), lambda _: None)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["rsrp"], -100)
        self.assertEqual(self.backend.config().lte_band, "800d5")

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_cancel_scan_restores_baseline(self):
        cancelled = threading.Event()
        def report(event):
            if event.get("status") == "Configurazione":
                cancelled.set()
        result = self.backend.scan([3, 7], cancelled, report)
        self.assertEqual(result, [])
        self.assertEqual(self.backend.config().lte_band, "800d5")
        self.assertEqual(self.backend.client.net.writes, [])

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_cancel_during_readback_restores_baseline(self):
        cancelled = threading.Event()
        net = self.backend.client.net
        original_write = net.set_net_mode

        def write_then_cancel(**kwargs):
            original_write(**kwargs)
            cancelled.set()

        net.set_net_mode = write_then_cancel
        result = self.backend.scan([3, 7], cancelled, lambda _: None)
        self.assertEqual(result, [])
        self.assertEqual(net.current["LTEBand"], "800d5")
        self.assertEqual([write[0] for write in net.writes], ["4", "800d5"])

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_cancel_after_completed_band_keeps_only_completed_results(self):
        cancelled = threading.Event()

        def report(event):
            if event.get("status") == "OK":
                cancelled.set()

        result = self.backend.scan([3, 7], cancelled, report)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["band"], 3)
        self.assertEqual(result[0]["status"], "OK")
        self.assertEqual(self.backend.config().lte_band, "800d5")

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_scan_with_only_mode_and_psatt_is_not_ok(self):
        self.backend.client.device.signal = lambda: {
            "mode": "7", "psatt": "1", "rsrp": "", "rsrq": "",
            "rssi": "", "sinr": "", "pci": ""
        }
        results = self.backend.scan([7], threading.Event(), lambda _: None)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "Nessuna misura")
        self.assertIsNone(results[0]["rsrp"])
        self.assertIsNone(results[0]["sinr"])
        self.assertEqual(self.backend.config().lte_band, "800d5")

    def test_reject_nonlocal_host(self):
        with self.assertRaises(ValueError):
            HuaweiRadioBackend("8.8.8.8", "admin", "test")


if __name__ == "__main__":
    unittest.main()

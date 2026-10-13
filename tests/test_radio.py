"""Pure radio + mocked Huawei interface tests (never touches a modem)."""

import threading
import unittest
from unittest.mock import patch

from pocket_manager.backend import HuaweiRadioBackend, RadioError
from pocket_manager.radio import (
    RadioConfig, bands_from_mask, mask_hex, normalized_mask,
    numeric_metric, parse_mask, safe_json_data, supported_bands,
    has_radio_measurements, network_overview, band_indicator,
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

    def test_single_allowed_band_is_deduced_only_when_4g_connected(self):
        cfg = {"LTEBand": "40", "NetworkMode": "00"}
        status = {"ConnectionStatus": "901", "CurrentNetworkType": "19"}
        plmn = {"Rat": "7"}
        out = band_indicator(cfg, status, plmn, {"lte_bandinfo": None})
        self.assertEqual((out.band, out.source), (7, "deduced"))
        self.assertEqual(out.label, "B7 · dedotta")
        self.assertIn("unica banda possibile", out.detail)
        disconnected = band_indicator(cfg, {"ConnectionStatus": "902"}, plmn, {})
        self.assertEqual(disconnected.source, "unknown")
        self.assertIsNone(disconnected.band)

    def test_multiple_allowed_bands_do_not_fabricate_serving_band(self):
        status = {"ConnectionStatus": "901", "CurrentNetworkType": "19"}
        plmn = {"Rat": "7"}
        out = band_indicator({"LTEBand": "800d5"}, status, plmn, {"lte_bandinfo": None})
        self.assertEqual(out.label, "Non rilevabile")
        self.assertEqual(out.source, "unknown")
        self.assertEqual(out.allowed, (1, 3, 5, 7, 8, 20))

    def test_explicit_lte_bandinfo_can_override_multiple_allowed_bands(self):
        status = {"ConnectionStatus": "901", "CurrentNetworkType": "19"}
        plmn = {"Rat": "7"}
        out = band_indicator({"LTEBand": "800d5"}, status, plmn,
                             {"lte_bandinfo": "LTE Band 3"})
        self.assertEqual(out.label, "B3 · rilevata")
        self.assertEqual(out.source, "api")

    def test_unsupported_or_inconsistent_firmware_band_is_not_claimed(self):
        status = {"ConnectionStatus": "901", "CurrentNetworkType": "19"}
        plmn = {"Rat": "7"}
        unknown = band_indicator({"LTEBand": "800d5"}, status, plmn,
                                 {"lte_bandinfo": "B28"})
        self.assertEqual(unknown.source, "unknown")
        unknown = band_indicator({"LTEBand": "800d5"}, status, plmn,
                                 {"lte_bandinfo": "1800 MHz"})
        self.assertEqual(unknown.source, "unknown")
        self.assertEqual(band_indicator({}, status, plmn, {}).source, "unknown")

    def test_unknown_extra_mask_bits_never_create_single_band_deduction(self):
        # Band 3 plus an unrecognised band outside this firmware's known list.
        mask = hex((1 << (3 - 1)) | (1 << (28 - 1)))
        state = {"ConnectionStatus": "901", "CurrentNetworkType": "19"}
        out = band_indicator({"LTEBand": mask}, state, {"Rat": "7"}, {})
        self.assertEqual(out.source, "unknown")
        self.assertIn("e altre", out.detail)

    def test_real_e5577_status_has_connection_without_rf_measurements(self):
        # Sanitized Dell observation: firmware 21.328.62.00.55.
        status = {
            "ConnectionStatus": "901", "CurrentNetworkType": "19",
            "SimStatus": "1", "SignalIcon": "1", "maxsignal": "5",
            "SignalStrength": None,
        }
        signal = {"mode": "7", "psatt": "1", "rsrp": None,
                  "rsrq": None, "sinr": None, "rssi": None, "pci": None}
        result = network_overview(status, {"FullName": "WINDTRE"}, signal)
        self.assertEqual(result["connection"], "Connessa (secondo firmware)")
        self.assertEqual(result["network"], "4G LTE")
        self.assertEqual(result["sim"], "Pronta")
        self.assertEqual(result["operator"], "WINDTRE")
        self.assertEqual(result["bars"], "1/5 tacche (indicatore firmware)")
        self.assertIn("indisponibili", result["rf"])
        self.assertFalse(has_radio_measurements(signal))

    def test_unknown_status_does_not_invent_connection_or_signal(self):
        result = network_overview({"__error__": "100002"}, {}, {})
        self.assertEqual(result["connection"], "Non disponibile")
        self.assertEqual(result["bars"], "Non disponibile")
        self.assertEqual(result["network"], "Non disponibile")
        result = network_overview({"ConnectionStatus": "902",
                                   "SignalIcon": "5", "maxsignal": "5"}, {}, {})
        self.assertEqual(result["connection"], "Disconnessa")

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

    def information(self):
        return {"DeviceName": "E5577Cs-321", "Imei": "PRIVATE"}


class FakeMonitoring:
    def status(self):
        return {"ConnectionStatus": "901"}

    def traffic_statistics(self):
        return {"CurrentDownloadRate": "4096", "CurrentUploadRate": "2048"}


class FakeClient:
    def __init__(self):
        self.net = FakeNet()
        self.device = FakeDevice()
        self.monitoring = FakeMonitoring()


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = HuaweiRadioBackend("192.168.8.1", "admin", "test")
        self.backend.client = FakeClient()

    def test_periodic_snapshot_refreshes_status(self):
        snapshot = self.backend.snapshot()
        self.assertEqual(snapshot["monitoring_status"]["ConnectionStatus"], "901")
        self.assertEqual(snapshot["traffic_statistics"]["CurrentDownloadRate"], "4096")
        self.assertNotIn("device_information", snapshot)

    def test_full_snapshot_includes_status_and_auth_model(self):
        snapshot = self.backend.snapshot(full=True)
        self.assertEqual(snapshot["device_information"]["DeviceName"], "E5577Cs-321")
        self.assertEqual(snapshot["monitoring_status"]["ConnectionStatus"], "901")
        self.assertNotIn("Imei", safe_json_data(snapshot["device_information"]))

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

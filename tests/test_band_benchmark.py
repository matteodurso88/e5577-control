"""Offline band benchmark tests; never send Internet traffic or change a modem."""

from datetime import datetime
import json
import subprocess
import threading
import unittest
from unittest.mock import patch

from pocket_manager.band_benchmark import (
    BandResult, BenchmarkError, DownloadSample, Egress, check_route,
    lte_connected, ranking, run_band_benchmark,
)
from pocket_manager.radio import RadioConfig


class RoutingTests(unittest.TestCase):
    def test_wrong_wan_is_rejected_before_benchmark(self):
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, json.dumps([{
                "dst": "162.159.140.220", "gateway": "192.168.100.1",
                "dev": "wlp0s20f3", "prefsrc": "192.168.100.18",
            }]))
        with patch("sys.platform", "linux"):
            with self.assertRaisesRegex(BenchmarkError, "NON attraverso il pocket"):
                check_route("192.168.8.1", "162.159.140.220", run=fake_run)

    def test_direct_pocket_route_is_accepted(self):
        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, json.dumps([{
                "dst": "162.159.140.220", "gateway": "192.168.8.1",
                "dev": "wlp0s20f3", "prefsrc": "192.168.8.42",
            }]))
        with patch("sys.platform", "linux"):
            result = check_route("192.168.8.1", "162.159.140.220", run=fake_run)
        self.assertEqual(result.gateway, "192.168.8.1")
        self.assertEqual(result.source, "192.168.8.42")

    def test_unknown_platform_fails_closed(self):
        with patch("sys.platform", "win32"):
            with self.assertRaisesRegex(BenchmarkError, "solo su Linux"):
                check_route("192.168.8.1", "162.159.140.220")

    def test_huawei_lte_status_not_just_connected(self):
        self.assertTrue(lte_connected(
            {"ConnectionStatus": "901", "CurrentNetworkType": "19"},
            {"Rat": "7"}))
        self.assertFalse(lte_connected(
            {"ConnectionStatus": "901", "CurrentNetworkType": "7"},
            {"Rat": "2"}))


class FakeNet:
    def net_mode_list(self):
        return {"LTEBandList": {"LTEBand": [{"Value": "800d5"}]}}


class FakeRadio:
    host = "192.168.8.1"

    def __init__(self):
        self.baseline = RadioConfig("40", "3FFFFFFF", "00")
        self.current = self.baseline
        self.client = type("Client", (), {"net": FakeNet()})()
        self.writes = []

    def config(self):
        return self.current

    def _read(self, group, method):
        return getattr(group, method)()

    def _write_verified(self, target, **kwargs):
        self.current = target
        self.writes.append(target.lte_band)
        return target

    def snapshot(self):
        return {
            "monitoring_status": {"ConnectionStatus": "901", "CurrentNetworkType": "19"},
            "plmn": {"Rat": "7"},
        }


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.radio = FakeRadio()
        self.egress = Egress("162.159.140.220", "192.168.8.1",
                             "wlp0s20f3", "192.168.8.42")
        self.stop = threading.Event()
        self.progress = []

    def route(self, host, dst):
        self.assertEqual(host, self.radio.host)
        return self.egress

    def run_bands(self, bands, **extra):
        return run_band_benchmark(
            self.radio, bands, self.stop, self.progress.append,
            route_checker=extra.pop("route_checker", self.route),
            resolver=lambda: self.egress.destination,
            downloader=extra.pop("downloader", lambda *a, **k: DownloadSample(12.5, 45, 1048576)),
            repeats=extra.pop("repeats", 2),
            bytes_per_sample=extra.pop("bytes_per_sample", 1_048_576),
            settle_seconds=0.05, sleeper=lambda _: None, **extra,
        )

    def test_failed_route_cannot_write_radio(self):
        def reject(host, dst):
            raise BenchmarkError("Wrong WAN")
        with self.assertRaisesRegex(BenchmarkError, "Wrong WAN"):
            self.run_bands([3], route_checker=reject)
        self.assertEqual(self.radio.writes, [])

    def test_two_bands_with_median_speed_and_original_mode_restored(self):
        self.radio.current = RadioConfig("40", "3FFFFFFF", "00")
        def download(route, *, bytes_requested):
            current = self.radio.current.lte_band
            return DownloadSample(30 if current == "4" else 15, 60 if current == "4" else 40,
                                  bytes_requested)
        rows = self.run_bands([3, 7], downloader=download)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].med_mbps, 30)
        self.assertEqual(rows[1].med_mbps, 15)
        self.assertEqual(ranking(rows)[0].band, 3)
        self.assertTrue(self.radio.current.matches(self.radio.baseline))
        self.assertTrue(all(config in ("4", "40") for config in self.radio.writes))

    def test_cancel_during_first_band_restores_baseline(self):
        def first_download(route, **kwargs):
            self.stop.set()
            return DownloadSample(10, 100, kwargs["bytes_requested"])
        rows = self.run_bands([3, 7], downloader=first_download)
        self.assertEqual(rows, [])
        self.assertTrue(self.radio.current.matches(self.radio.baseline))
        self.assertEqual(self.radio.writes, ["4", "40"])

    def test_unsupported_band_fails_before_write(self):
        with self.assertRaisesRegex(BenchmarkError, "non risultano supportate"):
            self.run_bands([28])
        self.assertEqual(self.radio.writes, [])

    def test_bad_budget_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bands([3], repeats=4)
        self.assertEqual(self.radio.writes, [])

    def test_route_changed_stops_and_restores(self):
        calls = []
        def drift(host, dst):
            calls.append(True)
            if len(calls) >= 2:
                return Egress(dst, "192.168.100.1", "wlp0s20f3", "192.168.100.18")
            return self.egress
        rows = self.run_bands([3, 7], route_checker=drift)
        self.assertEqual(rows[0].status, "Errore")
        self.assertTrue(self.radio.current.matches(self.radio.baseline))
        self.assertEqual(self.radio.writes, ["4", "40"])

    def test_mismatched_sample_count_has_no_ranking(self):
        a = BandResult(3, "4", "OK", 30, 100, 2)
        b = BandResult(7, "40", "OK", 40, 120, 1)
        self.assertEqual(ranking([a, b]), [])


if __name__ == "__main__":
    unittest.main()

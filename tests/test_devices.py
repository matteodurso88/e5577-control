"""No pocket, GUI, network or real credential vault required for these tests."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocket_manager.discovery import (
    candidates_from_interfaces, parse_device_information, parse_compatible_endpoint,
    probe, probe_detailed, discover, discover_report
)
from pocket_manager.profiles import (
    CredentialStoreError, PocketProfile, ProfileStore, SERVICE
)


class FakeVault:
    def __init__(self):
        self.data = {}
        self.fail = False

    def set_password(self, service, username, password):
        if self.fail:
            raise RuntimeError("vault locked")
        self.data[service, username] = password

    def get_password(self, service, username):
        if self.fail:
            raise RuntimeError("vault locked")
        return self.data.get((service, username))

    def delete_password(self, service, username):
        self.data.pop((service, username), None)


class DiscoveryTests(unittest.TestCase):
    def test_bounded_host_candidates(self):
        hosts = candidates_from_interfaces([
            ("192.168.12.25", "255.255.255.0"),
            ("10.1.2.30", "255.255.0.0"),
            ("127.0.0.1", "255.0.0.0"),
        ], ("192.168.8.73", "8.8.8.8", "invalid"))
        self.assertIn("192.168.8.1", hosts)
        self.assertIn("192.168.8.73", hosts)
        self.assertIn("192.168.12.1", hosts)
        self.assertIn("192.168.12.254", hosts)
        self.assertIn("10.1.2.1", hosts)
        self.assertNotIn("8.8.8.8", hosts)
        self.assertNotIn("127.0.0.1", hosts)
        self.assertLessEqual(len(hosts), 32)

    def test_parse_huawei_information(self):
        payload = b"<response><Manufacturer>Huawei</Manufacturer><DeviceName>E5577Cs-321</DeviceName></response>"
        device = parse_device_information(payload, "192.168.8.1")
        self.assertEqual(device.model, "E5577Cs-321")
        self.assertEqual(device.url, "http://192.168.8.1/")

    def test_ignores_unverified_router(self):
        self.assertIsNone(parse_device_information(
            b"<response><DeviceName>Generic Router</DeviceName></response>", "192.168.1.1"))
        self.assertIsNone(parse_device_information(
            b"<error><code>100003</code></error>", "192.168.8.1"))
        self.assertIsNone(probe("8.8.8.8"))

    def test_information_auth_error_but_anonymous_signal_succeeds(self):
        def fetch(host, endpoint, timeout):
            if endpoint == "api/device/information":
                return b"<error><code>100003</code></error>", "HTTP 200"
            if endpoint == "api/device/signal":
                return b"<response><rsrp>-91dBm</rsrp><sinr>12dB</sinr></response>", "HTTP 200"
            return None, "not probed"

        with patch("pocket_manager.discovery._fetch_api", side_effect=fetch):
            device, diagnostics = probe_detailed("192.168.8.1")
        self.assertIsNotNone(device)
        self.assertEqual(device.detection, "compatible_api")
        self.assertEqual(device.host, "192.168.8.1")
        self.assertNotIn("modello E5577", " ".join(diagnostics))

    def test_sestokinfo_fallback_recognizes_compatible_api_without_leaking_token(self):
        def fetch(host, endpoint, timeout):
            if endpoint.endswith("SesTokInfo"):
                return (b"<response><SesInfo>SessionID=privatesession</SesInfo>"
                        b"<TokInfo>SECRET-TOKEN</TokInfo></response>"), "HTTP 200"
            return None, "HTTP 403"

        with patch("pocket_manager.discovery._fetch_api", side_effect=fetch):
            device, diagnostics = probe_detailed("192.168.8.1")
        self.assertEqual(device.detection, "compatible_api")
        self.assertNotIn("SECRET-TOKEN", " ".join(diagnostics))
        self.assertNotIn("privatesession", " ".join(diagnostics))

    def test_unrelated_web_server_is_not_identified(self):
        def fetch(*args):
            return b"<html>OK</html>", "HTTP 200"

        with patch("pocket_manager.discovery._fetch_api", side_effect=fetch):
            device, diagnostics = probe_detailed("192.168.9.1")
        self.assertIsNone(device)
        self.assertIn("risposta non identificante", " ".join(diagnostics))

    def test_saved_and_manual_hosts_have_priority_over_many_interfaces(self):
        interfaces = [(f"10.{i}.0.50", "255.255.255.0") for i in range(1, 60)]
        hosts = candidates_from_interfaces(
            interfaces, ("192.168.8.44", "10.90.0.22"),
            ("192.168.8.1",)
        )
        self.assertLessEqual(len(hosts), 32)
        self.assertEqual(hosts[:3], ["192.168.8.44", "10.90.0.22", "192.168.8.1"])

    def test_report_includes_attempted_ips_and_results(self):
        from pocket_manager.discovery import DiscoveredPocket
        pocket = DiscoveredPocket("192.168.8.1", "E5577Cs-321", "E5577Cs-321", "Huawei")
        with patch("pocket_manager.discovery.host_candidates", return_value=["192.168.8.1"]):
            with patch("pocket_manager.discovery.probe_detailed", return_value=(pocket, ("192.168.8.1: identificato",))):
                report = discover_report()
        self.assertEqual(report.candidates, ("192.168.8.1",))
        self.assertEqual(report.devices[0].model, "E5577Cs-321")
        self.assertEqual(len(report.diagnostics), 1)


class ProfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = FakeVault()
        self.store = ProfileStore(Path(self.tmp.name), vault=self.vault)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_without_secret(self):
        profile = self.store.new_profile("Backup pocket", "192.168.8.1", model="E5577Cs-321")
        self.store.save(profile)
        self.assertEqual(self.store.list(), [profile])
        self.assertNotIn("password", self.store.file.read_text().lower())
        self.assertEqual(self.vault.data, {})

    def test_explicit_remember_and_fast_reconnect(self):
        profile = self.store.new_profile("Pocket casa", "192.168.8.1")
        self.store.save(profile, remember_password=True, password="s3cret")
        self.assertEqual(self.store.credential(profile.id), "s3cret")
        self.assertNotIn("s3cret", self.store.file.read_text())
        changed_host = PocketProfile(profile.id, profile.alias, "192.168.8.2", profile.username, profile.model)
        self.store.save(changed_host)
        self.assertEqual(self.store.credential(profile.id), "s3cret")
        self.assertEqual(self.store.list()[0].host, "192.168.8.2")
        self.store.delete(profile.id)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.credential(profile.id), None)

    def test_locked_vault_never_plaintext_fallback(self):
        profile = self.store.new_profile("Pocket", "192.168.8.1")
        self.vault.fail = True
        with self.assertRaises(CredentialStoreError):
            self.store.save(profile, remember_password=True, password="private")
        self.assertFalse(self.store.file.exists())

    def test_invalid_host_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.new_profile("Public endpoint", "1.1.1.1")
        with self.assertRaises(ValueError):
            self.store.new_profile("Invalid", "pocket.local")


if __name__ == "__main__":
    unittest.main()

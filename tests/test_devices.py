"""No pocket, GUI, network or real credential vault required for these tests."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocket_manager.discovery import (
    candidates_from_interfaces, parse_device_information, probe, discover
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

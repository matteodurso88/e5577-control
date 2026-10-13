"""Offline packaging checks; no PyInstaller execution or device access."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import tarfile
import unittest
from unittest.mock import patch
import zipfile

from pocket_manager import __version__
from scripts.build_desktop import package_bundle, target
from scripts.frozen_entry import main


class NativeBuildTests(unittest.TestCase):
    def test_linux_target_is_tarball(self):
        with patch("scripts.build_desktop.platform.system", return_value="Linux"), \
             patch("scripts.build_desktop.platform.machine", return_value="x86_64"):
            self.assertEqual(target(), ("linux-x86_64", ".tar.gz"))

    def test_windows_target_is_zip(self):
        with patch("scripts.build_desktop.platform.system", return_value="Windows"), \
             patch("scripts.build_desktop.platform.machine", return_value="AMD64"):
            self.assertEqual(target(), ("windows-x86_64", ".zip"))

    def test_unsupported_platform_refused(self):
        with patch("scripts.build_desktop.platform.system", return_value="Darwin"), \
             patch("scripts.build_desktop.platform.machine", return_value="arm64"):
            with self.assertRaises(SystemExit):
                target()

    def test_archives_only_frozen_app_folder(self):
        with TemporaryDirectory() as scratch:
            base = Path(scratch)
            bundle = base / "PocketRadioManager"
            bundle.mkdir()
            (bundle / "PocketRadioManager").write_bytes(b"fake-executable")
            internal = bundle / "_internal"
            internal.mkdir()
            (internal / "runtime.dat").write_bytes(b"nonsecret")

            # A nearby user-like file must never be archived.
            (base / "devices.json").write_text("DO-NOT-COPY", encoding="utf-8")

            zipped = base / "package.zip"
            package_bundle(bundle, zipped)
            with zipfile.ZipFile(zipped) as reader:
                names = reader.namelist()
                self.assertIn("PocketRadioManager/PocketRadioManager", names)
                self.assertIn("PocketRadioManager/_internal/runtime.dat", names)
                self.assertFalse(any("devices.json" in name for name in names))

            tarred = base / "package.tar.gz"
            package_bundle(bundle, tarred)
            with tarfile.open(tarred, "r:gz") as reader:
                names = reader.getnames()
                self.assertIn("PocketRadioManager/PocketRadioManager", names)
                self.assertFalse(any("devices.json" in name for name in names))

    def test_frozen_version_flag_does_not_launch_gui(self):
        stream = StringIO()
        # --version must never import the Qt GUI at all. Importing it here
        # would require native graphics libraries on the CI runner.
        import sys
        was_imported = "pocket_manager.qt_app" in sys.modules
        with redirect_stdout(stream):
            self.assertEqual(main(["--version"]), 0)
        self.assertEqual("pocket_manager.qt_app" in sys.modules, was_imported)
        self.assertIn(__version__, stream.getvalue())


if __name__ == "__main__":
    unittest.main()

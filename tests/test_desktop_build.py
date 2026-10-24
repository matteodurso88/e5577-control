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
            bundle = base / "E5577Control"
            bundle.mkdir()
            (bundle / "E5577Control").write_bytes(b"fake-executable")
            internal = bundle / "_internal"
            internal.mkdir()
            (internal / "runtime.dat").write_bytes(b"nonsecret")

            # A nearby user-like file must never be archived.
            (base / "devices.json").write_text("DO-NOT-COPY", encoding="utf-8")

            zipped = base / "package.zip"
            package_bundle(bundle, zipped)
            with zipfile.ZipFile(zipped) as reader:
                names = reader.namelist()
                self.assertIn("E5577Control/E5577Control", names)
                self.assertIn("E5577Control/_internal/runtime.dat", names)
                self.assertFalse(any("devices.json" in name for name in names))

            tarred = base / "package.tar.gz"
            package_bundle(bundle, tarred)
            with tarfile.open(tarred, "r:gz") as reader:
                names = reader.getnames()
                self.assertIn("E5577Control/E5577Control", names)
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


    def test_svg_icon_is_native_vector_with_accessible_title(self):
        from xml.etree import ElementTree
        source = Path(__file__).resolve().parents[1] / "assets" / "e5577-control-icon.svg"
        root = ElementTree.parse(source).getroot()
        self.assertEqual(root.get("viewBox"), "0 0 256 256")
        self.assertTrue(root.findall(".//{http://www.w3.org/2000/svg}path"))
        self.assertTrue(root.findall(".//{http://www.w3.org/2000/svg}title"))
        self.assertNotIn("<image", source.read_text(encoding="utf-8"))

    def test_canonical_matt88_wordmarks_are_svg_and_packaged(self):
        from xml.etree import ElementTree
        root = Path(__file__).resolve().parents[1]
        for variant in ("light", "dark"):
            logo = root / "assets" / "matt88" / f"logo-{variant}.svg"
            self.assertTrue(logo.is_file())
            tree = ElementTree.parse(logo).getroot()
            self.assertEqual(tree.get("viewBox"), "240 140 1735 440")
            self.assertIn("<title>matt88.it</title>", logo.read_text(encoding="utf-8"))

        build = (root / "scripts" / "build_desktop.py").read_text(encoding="utf-8")
        self.assertIn('"assets/matt88"', build)
        self.assertIn('"--add-data"', build)
        entry = (root / "scripts" / "frozen_entry.py").read_text(encoding="utf-8")
        self.assertIn("Missing canonical matt88.it branding asset", entry)

    def test_debian_menu_entry_is_correctly_scoped(self):
        desktop = (Path(__file__).resolve().parents[1] / "packaging" / "linux"
                   / "io.matt88.E5577Control.desktop").read_text(encoding="utf-8")
        self.assertIn("[Desktop Entry]", desktop)
        self.assertIn("Type=Application", desktop)
        self.assertIn("Name=E5577 Control", desktop)
        self.assertIn("Exec=/opt/e5577-control/E5577Control", desktop)
        self.assertIn("Icon=e5577-control", desktop)
        self.assertIn("Categories=Network;Utility;", desktop)

    def test_windows_installer_contains_start_menu_and_uninstall(self):
        setup = (Path(__file__).resolve().parents[1] / "packaging" / "windows"
                 / "E5577Control.iss").read_text(encoding="utf-8")
        self.assertIn("SetupIconFile={#IconFile}", setup)
        self.assertIn('Name: "{autoprograms}', setup)
        self.assertIn("UninstallDisplayIcon={app}", setup)
        self.assertIn("PrivilegesRequired=lowest", setup)
        self.assertIn('Name: "desktopicon"', setup)

    def test_product_ci_releases_only_from_annotated_version_tag(self):
        """Build on PR/main and release only a separately approved exact tag."""
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows"
                    / "e5577-control-desktop.yml").read_text(encoding="utf-8")
        self.assertIn("name: E5577 Control", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("python scripts/local_gate.py", workflow)
        self.assertIn("python scripts/build_desktop.py", workflow)
        self.assertIn("dist/packages/*", workflow)
        self.assertIn("1.0.0", __version__)
        self.assertNotIn("pocket-manager/", workflow)
        self.assertIn("tags: [v1.0.0]", workflow)
        self.assertIn("github.ref == 'refs/tags/v1.0.0'", workflow)
        self.assertIn("needs: package", workflow)
        self.assertIn("git cat-file -t", workflow)
        self.assertIn("git rev-parse", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn("docs/en/RELEASE_NOTES_v1.0.0.md", workflow)
        self.assertIn("docs/it/RELEASE_NOTES_v1.0.0.md", workflow)

    def test_bilingual_release_documentation_matches_target(self):
        root = Path(__file__).resolve().parents[1]
        for topic in ("OVERVIEW", "INSTALL", "USAGE", "SECURITY",
                      "ARCHITECTURE", "DEVELOPMENT", "RELEASE",
                      "RELEASE_NOTES_v1.0.0"):
            for lang in ("en", "it"):
                doc = root / "docs" / lang / (topic + ".md")
                self.assertTrue(doc.is_file(), f"Missing {doc}")
                self.assertGreater(doc.stat().st_size, 500)
        self.assertTrue((root / "docs" / "history" / "WORKSHOP_README.md").is_file())
        landing = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("## English", landing)
        self.assertIn("## Italiano", landing)
        self.assertIn("docs/en/INSTALL.md", landing)
        self.assertIn("docs/it/INSTALL.md", landing)


if __name__ == "__main__":
    unittest.main()

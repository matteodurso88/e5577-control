"""PyInstaller-friendly entrypoint for E5577 Control desktop bundles.

--version and --self-check run without Qt GUI initialization, radio access,
network traffic, saved profiles, or credentials. The normal path starts Qt.
"""

from __future__ import annotations

import argparse
import sys

from pocket_manager import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="E5577Control")
    parser.add_argument("--version", action="store_true", help="Show application version")
    parser.add_argument(
        "--self-check", action="store_true",
        help="Import bundled runtime modules without touching a modem",
    )
    args = parser.parse_args(argv)
    if args.version:
        if sys.stdout is not None:
            print(f"E5577 Control {__version__}")
        return 0

    if args.self_check:
        # Import-based smoke: verifies frozen modules and Qt shared libraries
        # can be loaded. Does NOT create QApplication, contact any host,
        # query OS credentials or mutate radio / WAN configuration.
        import platformdirs  # noqa: F401
        import psutil  # noqa: F401
        import keyring  # noqa: F401
        from PySide6.QtWidgets import QApplication  # noqa: F401
        from huawei_lte_api.Client import Client  # noqa: F401
        from huawei_lte_api.Connection import Connection  # noqa: F401
        from pocket_manager.backend import HuaweiRadioBackend  # noqa: F401
        from pocket_manager.profiles import ProfileStore  # noqa: F401
        from pocket_manager.qt_app import PocketWindow  # noqa: F401

        if sys.platform.startswith("linux"):
            import keyring.backends.SecretService  # noqa: F401
        elif sys.platform == "win32":
            import keyring.backends.Windows  # noqa: F401
        if sys.stdout is not None:
            print(f"PASS: E5577 Control {__version__} runtime imports")
        return 0

    # Preserve exactly one QApplication instance, managed by the Qt entrypoint.
    from pocket_manager.qt_app import main as qt_main
    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main())

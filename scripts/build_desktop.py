"""Build unsigned portable desktop archives natively on Linux/Windows.

Install package and PyInstaller, then run this script on each TARGET OS.
PyInstaller does not cross-compile. This script never reads user credentials,
creates modem sessions or changes radio settings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version as installed_version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

from pocket_manager import __version__

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "PocketRadioManager"
BUNDLE_PARENT = ROOT / "dist" / "bundles"
OUTPUT_DIR = ROOT / "dist" / "packages"
WORK_DIR = ROOT / "build" / "pyinstaller"
ENTRYPOINT = ROOT / "scripts" / "frozen_entry.py"


def target() -> tuple[str, str]:
    if platform.system() == "Linux" and platform.machine().lower() in ("x86_64", "amd64"):
        return "linux-x86_64", ".tar.gz"
    if platform.system() == "Windows" and platform.machine().lower() in ("amd64", "x86_64"):
        return "windows-x86_64", ".zip"
    raise SystemExit("Build desktop supportata solo su Linux x86-64 e Windows x64")


def dependency_versions() -> dict[str, str]:
    result = {}
    for name in ("pyinstaller", "PySide6", "huawei-lte-api",
                 "keyring", "platformdirs", "psutil", "SecretStorage"):
        try:
            result[name] = installed_version(name)
        except PackageNotFoundError:
            result[name] = "not installed"
    return result


def package_bundle(bundle: Path, archive: Path) -> None:
    """Archive ONLY the frozen application folder, never the source tree."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as output:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    output.write(path, arcname=path.relative_to(bundle.parent))
    else:
        with tarfile.open(archive, "w:gz") as output:
            output.add(bundle, arcname=bundle.name, recursive=True)


def run() -> int:
    platform_name, extension = target()
    BUNDLE_PARENT.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = BUNDLE_PARENT / APP_NAME
    if bundle.exists():
        shutil.rmtree(bundle)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", APP_NAME,
        "--distpath", str(BUNDLE_PARENT),
        "--workpath", str(WORK_DIR / "work"),
        "--specpath", str(WORK_DIR / "spec"),
        "--collect-submodules", "huawei_lte_api",
        "--collect-submodules", "keyring.backends",
        "--collect-submodules", "platformdirs",
        str(ENTRYPOINT),
    ]
    if sys.platform.startswith("linux"):
        command[ -1 : -1 ] = ["--collect-submodules", "secretstorage"]
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    executable = bundle / (APP_NAME + (".exe" if os.name == "nt" else ""))
    if not executable.is_file():
        raise RuntimeError("Missing compiled executable: " + str(executable))

    # Both gates are offline: no QApplication or modem connection.
    for flag in ("--version", "--self-check"):
        print(f"Smoke: {executable.name} {flag}", flush=True)
        subprocess.run([str(executable), flag], cwd=ROOT,
                       check=True, timeout=75)

    metadata = {
        "name": "Pocket Radio Manager",
        "version": __version__,
        "platform": platform_name,
        "architecture": platform.machine(),
        "commit": os.environ.get("GITHUB_SHA", "local-unverified"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies": dependency_versions(),
        "format": "portable unsigned application (not installer)",
    }
    (bundle / "BUILD-MANIFEST.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    startup = (
        "Pocket Radio Manager " + __version__ + "\n"
        "Portable, unsigned desktop build — " + platform_name + "\n\n"
        "Run " + executable.name + " from the extracted PocketRadioManager folder.\n"
        "Never run the executable from inside the ZIP/TAR.GZ archive.\n"
        "Requires a desktop session and local access to your Huawei pocket.\n"
        "Linux: executable permissions are preserved in the tar.gz archive.\n"
        "No login information, passwords or devices.json are bundled.\n"
        "Credentials can be saved only in a supported OS secure keyring.\n"
        "Commands: --version and --self-check (offline, no modem changes).\n"
        "Windows: unsigned builds may trigger a SmartScreen warning.\n"
        "Untrusted download? Verify the SHA256SUMS.txt checksum first.\n"
    )
    (bundle / "README-FIRST.txt").write_text(startup, encoding="utf-8")

    archive = OUTPUT_DIR / f"pocket-radio-manager-v{__version__}-{platform_name}{extension}"
    if archive.exists():
        archive.unlink()
    package_bundle(bundle, archive)
    hasher = sha256()
    with archive.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    checksum = OUTPUT_DIR / "SHA256SUMS.txt"
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"READY: {archive} ({archive.stat().st_size:,} bytes)", flush=True)
    print(f"SHA256: {digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

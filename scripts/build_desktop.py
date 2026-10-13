"""Build portable and installable desktop packages natively on Linux/Windows.

Run on Linux x86-64 or Windows x64 with the build dependencies installed.
No modem connection, credential reads, device writes or user data included.
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
    raise SystemExit("Build supportata solo su Linux x86-64 e Windows x64")


def dependency_versions() -> dict[str, str]:
    result = {}
    for name in ("pyinstaller", "PySide6", "huawei-lte-api", "keyring",
                 "platformdirs", "psutil", "SecretStorage", "Pillow"):
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


def build_deb(bundle: Path, png: Path) -> Path:
    """Create a native Ubuntu/Debian package with an app-menu entry and icon."""
    if not sys.platform.startswith("linux"):
        raise ValueError(".deb packaging requires a Linux host")
    stage = ROOT / "build" / "deb-root"
    if stage.exists():
        shutil.rmtree(stage)
    app_dir = stage / "opt" / "pocket-radio-manager"
    app_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, app_dir, symlinks=False)
    executable = app_dir / APP_NAME
    if not executable.exists():
        raise RuntimeError("Binary mancante dal pacchetto Debian")
    executable.chmod(0o755)

    desktop_src = ROOT / "packaging" / "linux" / "io.matt88.PocketRadioManager.desktop"
    desktop_dest = stage / "usr" / "share" / "applications" / desktop_src.name
    desktop_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(desktop_src, desktop_dest)
    desktop_dest.chmod(0o644)

    icon_dest = (stage / "usr" / "share" / "icons" / "hicolor"
                 / "256x256" / "apps" / "pocket-radio-manager.png")
    icon_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(png, icon_dest)
    icon_dest.chmod(0o644)

    control_dir = stage / "DEBIAN"
    control_dir.mkdir()
    (control_dir / "control").write_text(
        "Package: pocket-radio-manager\n"
        f"Version: {__version__}\n"
        "Section: net\n"
        "Priority: optional\n"
        "Architecture: amd64\n"
        "Maintainer: matteodurso88\n"
        "Depends: libc6, libstdc++6, libegl1, libgl1, libxcb-cursor0, libxkbcommon-x11-0\n"
        "Description: Pocket Radio Manager LTE desktop application\n"
        " Monitor Huawei pocket LTE connection, mobile data and read SMS.\n",
        encoding="utf-8",
    )
    archive = OUTPUT_DIR / f"pocket-radio-manager-v{__version__}-linux-x86_64.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                    str(stage), str(archive)], check=True, cwd=ROOT)
    subprocess.run(["dpkg-deb", "--field", str(archive), "Package"],
                   check=True, cwd=ROOT)
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError("Pacchetto Debian non creato")
    return archive


def find_inno_compiler() -> Path:
    candidates = [
        os.environ.get("INNO_SETUP_COMPILER", ""),
        shutil.which("ISCC.exe") or "",
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                     "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"),
                     "Inno Setup 6", "ISCC.exe"),
    ]
    for item in candidates:
        if item and Path(item).is_file():
            return Path(item)
    raise RuntimeError("Inno Setup 6 (ISCC.exe) non disponibile sul runner Windows")


def build_windows_installer(bundle: Path, ico: Path) -> Path:
    if os.name != "nt":
        raise ValueError("Windows installer requires Windows")
    compiler = find_inno_compiler()
    script = ROOT / "packaging" / "windows" / "PocketRadioManager.iss"
    expected = OUTPUT_DIR / (
        f"pocket-radio-manager-v{__version__}-windows-x86_64-setup.exe"
    )
    command = [
        str(compiler),
        f"/DSourceDir={bundle}",
        f"/DOutputDir={OUTPUT_DIR}",
        f"/DIconFile={ico}",
        f"/DAppVersion={__version__}",
        str(script),
    ]
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, timeout=360)
    if not expected.is_file() or expected.stat().st_size == 0:
        raise RuntimeError("Installer Inno Setup non creato")
    return expected


def record_sha256(files: list[Path]) -> Path:
    sums = []
    for archive in files:
        hasher = sha256()
        with archive.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(block)
        digest = hasher.hexdigest()
        sums.append(f"{digest}  {archive.name}")
        print(f"READY: {archive} ({archive.stat().st_size:,} bytes)", flush=True)
        print(f"SHA256: {digest}", flush=True)
    checksum_file = OUTPUT_DIR / "SHA256SUMS.txt"
    checksum_file.write_text("\n".join(sums) + "\n", encoding="ascii")
    return checksum_file


def run() -> int:
    from scripts.generate_icons import generate

    platform_name, extension = target()
    png, ico = generate()
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
        "--add-data", str(png) + os.pathsep + ".",
        "--collect-submodules", "huawei_lte_api",
        "--collect-submodules", "keyring.backends",
        "--collect-submodules", "platformdirs",
    ]
    if sys.platform.startswith("linux"):
        command += ["--collect-submodules", "secretstorage"]
    else:
        command += ["--icon", str(ico)]
    command.append(str(ENTRYPOINT))
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    executable = bundle / (APP_NAME + (".exe" if os.name == "nt" else ""))
    if not executable.is_file():
        raise RuntimeError("Missing compiled executable: " + str(executable))

    # Version and import checks run on the native frozen executable, offline.
    for flag in ("--version", "--self-check"):
        print(f"Smoke: {executable.name} {flag}", flush=True)
        subprocess.run([str(executable), flag], cwd=ROOT, check=True, timeout=75)

    metadata = {
        "name": "Pocket Radio Manager",
        "version": __version__,
        "platform": platform_name,
        "architecture": platform.machine(),
        "commit": os.environ.get("GITHUB_SHA", "local-unverified"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies": dependency_versions(),
        "format": "portable plus OS-native installer; unsigned",
        "icon": "pocket-radio-manager-icon.svg (native vector source)",
    }
    (bundle / "BUILD-MANIFEST.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (bundle / "README-FIRST.txt").write_text(
        f"Pocket Radio Manager v{__version__}\n"
        "Run the executable from the extracted folder. The installers register "
        "the application in Linux's application menu or the Windows Start Menu.\n"
        "No saved profiles, credentials or SMS are bundled.\n"
        "These binaries are currently unsigned.\n",
        encoding="utf-8",
    )

    portable = OUTPUT_DIR / (
        f"pocket-radio-manager-v{__version__}-{platform_name}{extension}"
    )
    if portable.exists():
        portable.unlink()
    package_bundle(bundle, portable)
    installer = (build_deb(bundle, png) if platform_name.startswith("linux")
                 else build_windows_installer(bundle, ico))
    record_sha256([portable, installer])
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

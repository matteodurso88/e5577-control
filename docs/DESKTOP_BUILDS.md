# E5577 Control — desktop builds (v1.0.0 candidate)

Product repository: https://github.com/matteodurso88/e5577-control

> **Not released.** This document describes candidate output names and manual checks, not verified published downloads. The historical WORKSHOP `pocket-radio-manager/v0.1.0` release remains in the [provenance ledger](WORKSHOP_PROVENANCE.md).

## Packages expected from the two-platform CI

| OS | Native installer | Portable |
| --- | --- | --- |
| Ubuntu/Debian x86-64 | `e5577-control-v1.0.0-linux-x86_64.deb` | `e5577-control-v1.0.0-linux-x86_64.tar.gz` |
| Windows 10/11 x86-64 | `e5577-control-v1.0.0-windows-x86_64-setup.exe` | `e5577-control-v1.0.0-windows-x86_64.zip` |

All builds remain unsigned. Candidate archives must never include profiles, passwords, tokens, local keyring material, or SMS.

### Ubuntu / Debian

The Debian package ID is `e5577-control`, with a desktop entry named **E5577 Control** (Network/Utility), the application in `/opt/e5577-control/` and icon in `/usr/share/icons/hicolor/256x256/apps/e5577-control.png`.

For a verified downloaded candidate:
```bash
sudo apt install ./e5577-control-v1.0.0-linux-x86_64.deb
```

Remove via `sudo apt remove e5577-control`. The earlier WORKSHOP package used the distinct ID `pocket-radio-manager`. If both are installed during migration, their entries may coexist; remove the old package explicitly after verification. Do **not** remove users' local profile data or OS keyring entries.

### Windows

Inno Setup installs **E5577 Control** per-user (non-admin default) with a Start Menu shortcut, optional Desktop shortcut and uninstall entry. The original Pocket Radio Manager Inno Setup `AppId` remains intentionally unchanged so the installer can recognize existing installs instead of orphaning them. `UsePreviousAppDir=yes` allows an existing folder to be reused; when starting from scratch, the new folder is named E5577 Control.

Windows SmartScreen can warn about unsigned packages; verify GitHub origin and checksums before execution.

### Reproducible build / verification

```bash
python -m pip install -e . "pyinstaller==6.16.0" "pillow==11.3.0"
QT_QPA_PLATFORM=offscreen python scripts/local_gate.py
QT_QPA_PLATFORM=offscreen python scripts/build_desktop.py
```

Windows requires Inno Setup 6, Linux requires `dpkg-deb` and Qt system libraries.

The CI runs on pull requests and main. **It does not automatically create GitHub Releases.** Version, GUI About dialog, offline Qt tests, native package generation, frozen `--version` and `--self-check` need to pass on both platforms. Hardware validation, GUI visual smoke and install/uninstall acceptance on actual PCs remain separate gates.

### Backward-compatible profiles

The Python module is still `pocket_manager` and the secure credential service name is still `io.matt88.pocket-radio-manager`; default profile directory `pocket-radio-manager` remains unchanged to preserve previously saved devices and secrets. Do not rename these without a tested migration plan.

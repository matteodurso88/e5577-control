# Installation and upgrades — EN

[Italiano](../it/INSTALL.md) · [Home](../../README.md)

## Requirements

- **Linux:** x86-64 Ubuntu/Debian desktop; native `.deb` depends on `libc6`, `libstdc++6`, `libegl1`, `libgl1`, `libxcb-cursor0`, `libxkbcommon-x11-0`.
- **Windows:** Windows 10/11 x86-64, per-user installer; optional portable ZIP.
- A reachable **Huawei E5577Cs-321** and its administrator credentials are required for physical modem functions; not for opening the interface or running offline tests.

## Trusted source and checksums

Download **v1.0.0** only from [the Product Releases page](https://github.com/matteodurso88/e5577-control/releases/tag/v1.0.0) after the release is actually published. This release is expected to include:

| OS | Recommended installer | Portable alternative |
| --- | --- | --- |
| Linux x86-64 | `e5577-control-v1.0.0-linux-x86_64.deb` | `e5577-control-v1.0.0-linux-x86_64.tar.gz` |
| Windows x86-64 | `e5577-control-v1.0.0-windows-x86_64-setup.exe` | `e5577-control-v1.0.0-windows-x86_64.zip` |

Always verify `SHA256SUMS.txt` from the **same release** and directory as the four files. Linux: `sha256sum -c SHA256SUMS.txt`; Windows: `Get-FileHash .\e5577-control-v1.0.0-windows-x86_64-setup.exe -Algorithm SHA256` and compare with the checksum file. Packages are **unsigned**; a Windows SmartScreen warning is possible. A checksum verifies integrity relative to the published manifest, not publisher identity.

## Linux

```bash
sudo apt install ./e5577-control-v1.0.0-linux-x86_64.deb
```

Launch **E5577 Control** from Network/Utility applications. The executable installs under `/opt/e5577-control/`, and the desktop entry under `/usr/share/applications/`. For removal: `sudo apt remove e5577-control`. To use the portable archive, extract it and launch `E5577Control` from its extracted directory; do not move the executable away from the bundled libraries.

## Windows

Run the verified `e5577-control-v1.0.0-windows-x86_64-setup.exe`. Installation defaults to your user's `AppData\Local\Programs\E5577 Control`, with a Start Menu entry and uninstall support; a desktop icon is optional. For portable use, extract the entire ZIP and run `E5577Control.exe`. Do not extract just the EXE.

## Upgrading from Pocket Radio Manager v0.1.0

The Product retains the legacy `pocket-radio-manager` profile directory, the secure keyring service `io.matt88.pocket-radio-manager`, and the Python import package `pocket_manager` to preserve saved devices. Linux package IDs differ (`pocket-radio-manager` versus `e5577-control`), so both app entries may coexist. Test the new app first, then optionally remove the old **package only**; do not erase the old data directory or credentials. Windows preserves the historical Inno Setup AppId to recognize existing installations; review the chosen install directory.

For troubleshooting and device-safe checks see [Usage](USAGE.md) and [Security](SECURITY.md).

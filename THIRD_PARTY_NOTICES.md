# Third-party software and licensing — E5577 Control v1.0.1

The GPL-3.0-or-later license covers the **E5577 Control application code**.
The bundled runtime includes third-party components with **their own** terms.
Copyrights, licenses and source availability for these dependencies are
independent of the application's license.

| Component | Function | Upstream / license information |
| --- | --- | --- |
| Qt 6 / PySide6 / Shiboken6 | Qt desktop UI and Python bindings | [Qt for Python](https://doc.qt.io/qtforpython-6/commercial/index.html), [Qt licensing](https://doc.qt.io/qt-6/licensing.html); Community distribution offers LGPLv3/GPL variants depending on module |
| huawei-lte-api | Local Huawei API client | [Source](https://github.com/Salamek/huawei-lte-api); follow its installed distribution metadata and original license |
| keyring / SecretStorage / platformdirs | OS credential storage / local paths | [keyring](https://github.com/jaraco/keyring), [SecretStorage](https://github.com/mitya57/secretstorage), [platformdirs](https://github.com/tox-dev/platformdirs) — original projects' license terms apply |
| psutil | Host telemetry and network routing | [Source](https://github.com/giampaolo/psutil); original license applies |
| PyInstaller | Build-time freezer | [PyInstaller](https://pyinstaller.org/) and [bootloader licensing](https://pyinstaller.org/en/stable/license.html); GPL plus bootloader exception |
| Pillow | Build-time icon renderer | [Source](https://python-pillow.github.io/); Pillow HPND license |
| Inno Setup | Windows installer generator | [Inno Setup](https://jrsoftware.org/isinfo.php); separate Inno Setup license applies |

**The table is informational, not an exhaustive transitive-dependency or
Qt-module license inventory.** Packaging uses installed dependency versions;
`BUILD-MANIFEST.json` records the versions in each native artifact. Examine
the version-specific wheel/package contents and their bundled notices when
redistributing. Do not remove license files or copyright statements belonging
to any dependency.

## LGPL v3 / Qt replacement path

Qt/PySide6 Community libraries may be licensed under the LGPL v3, subject to
module-specific exceptions. The license text is in `LICENSES/LGPL-3.0-only.txt`
together with `LICENSE` (GPL v3). The distributed applications use a
**PyInstaller onedir** layout containing dynamically loaded Qt shared libraries
(`Qt6*.so` on Linux, `Qt6*.dll` on Windows). The complete extracted
directory must remain together; do not patch Qt DLLs while the app runs.

Recipients can obtain the complete E5577 Control source, modify it and build
their own application with a compatible version of PySide6/Qt, or inspect/
replace compatible bundled dynamic Qt libraries as allowed by the applicable
LGPL terms. No technological measures are intended to prevent using compatible
modified Qt libraries. The packaging uses no code-signature check that denies
execution of a modified Qt library. You must still satisfy any further
requirements for the particular Qt/third-party components you redistribute,
including applicable source-code availability and reverse-engineering rights.

To obtain source for the PySide6/Qt packages, follow the official
[Qt open-source source distributions](https://download.qt.io/official_releases/qt/)
and [Qt for Python sources](https://code.qt.io/cgit/pyside/pyside-setup.git/).
Version-specific source fulfillment must be checked for each published build:
an upstream download link alone may be insufficient to satisfy every LGPL
redistribution obligation. If the required source offer cannot be fulfilled,
do not redistribute that build.

## Trademark / brand

The complete matt88.it logo and wordmark in `assets/matt88/` remain separately
protected visual assets. See `NOTICE` and `docs/MATT88_BRANDING.md`. The GPL
license of the application does not grant rights to use matt88.it to identify
an unrelated product.

# Architecture — EN

[Italiano](../it/ARCHITECTURE.md) · [Home](../../README.md)

## Components

| Location | Responsibility |
| --- | --- |
| `pocket_manager/qt_app.py` | PySide6 main window, basic/advanced tabs, status cards, About dialog and canonical SVG footer |
| `pocket_manager/backend.py` | Huawei API session wrapper and guarded modem operations |
| `pocket_manager/discovery.py` | Constrained local endpoint discovery |
| `pocket_manager/profiles.py` | Local profile JSON, OS keyring, validation and safe atomic writes |
| `pocket_manager/radio.py` | LTE masks, modes, metrics, certainty-aware band presentation |
| `pocket_manager/band_benchmark.py` | Routing preflight, explicit LTE-band comparisons, recovery attempts |
| `pocket_manager/device_features.py` | SMS and mobile-data helpers |
| `pocket_manager/telemetry.py` | Bounded in-memory recent readings |
| `pocket_manager/presentation.py` | Human-facing labels and error wording |
| `scripts/local_gate.py` | Offline syntax and Python/Qt unit test gate |
| `scripts/build_desktop.py` | Native Linux/Windows frozen packaging, smoke, checksums |
| `scripts/frozen_entry.py` | Frozen entry point, `--version` and `--self-check` |
| `assets/matt88/` | Unmodified canonical light/dark SVG wordmarks |

## Execution and data flow

Qt's event loop runs UI widgets; separate `QThread` workers perform discovery and modem API calls. Radio jobs are queued to avoid blocking Qt and to serialize mutations; progress and results return through Qt signals. No GUI event handler should directly perform slow modem requests. Historic samples live in memory, without automatic persistent SMS storage.

Password handling crosses the OS keyring boundary only on explicit opt-in, and errors must not downgrade to plaintext storage. Connection failure and hardware measurements not reported by firmware must remain visible as unavailable, not as fabricated values. Band apply/scan/benchmark operations have explicit safety and recovery requirements.

## Distribution

- `pyproject.toml`: distribution name `e5577-control`, version `1.0.1`, CLI entry `e5577-control` and compatibility alias `pocket-radio-manager`; Python package remains `pocket_manager`.
- PyInstaller onedir: `E5577Control` / `E5577Control.exe`; native `.deb` and Inno Setup `.exe`; portable `.tar.gz` and `.zip`.
- Linux desktop entry: `packaging/linux/io.matt88.E5577Control.desktop`; Windows installer: `packaging/windows/E5577Control.iss`.
- Version and publisher in GUI: `v1.0.1`, About panel, complete 18px matt88.it wordmark in a 22px footer. The wordmark variant is selected from the Qt palette and bundled offline with the frozen app.
- All releases must be based on immutable exact Git tags; see [Release](RELEASE.md).

## Historical compatibility

The Product repository contains 124 commits extracted from the private WORKSHOP subtree. The original repository, PR and v0.1.0 release remain intact as history; see [provenance](../WORKSHOP_PROVENANCE.md). No rewrite of keyring service names or existing profile schema was introduced for the UI rebrand.

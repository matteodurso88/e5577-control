# E5577 Control v1.0.1 — GPL licensing update

**E5577 Control v1.0.1** supersedes v1.0.0, with no intended change to modem behaviour or the approved v1.0.0 user interface.

## Changes
- Application source licensed under **GNU GPL-3.0-or-later** (complete `LICENSE` and SPDX package metadata).
- All Linux/Windows native and portable distributions now include `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` and the `LICENSES/LGPL-3.0-only.txt` text for Qt/PySide6 licensing reference.
- Distribution-time `--self-check` verifies the notices exist, alongside the canonical matt88.it SVG assets. Debian installs a copyright notice under `/usr/share/doc/e5577-control/`.
- Dependency licensing and Qt source/relinking requirements are explained in `THIRD_PARTY_NOTICES.md`. The matt88.it wordmark remains separately protected branding; application source rights are unaffected.
- Bilingual English/Italian installation, security and release documentation updated to v1.0.1.
- After this replacement release has been published and validated, the **previous public v1.0.0 GitHub Release and its binary assets are withdrawn**. Its historical annotated Git tag and source history are preserved for provenance.

## Binaries
- Linux x86-64: `e5577-control-v1.0.1-linux-x86_64.deb` and `.tar.gz`.
- Windows x86-64: `e5577-control-v1.0.1-windows-x86_64-setup.exe` and `.zip`.
- `SHA256SUMS.txt` for all four packages.

**Packages are unsigned.** The primary hardware target remains Huawei E5577Cs-321. LTE-band changes and benchmarks can interrupt mobile data; offline CI tests do not substitute for hardware acceptance.

[EN documentation](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/docs/en/OVERVIEW.md) · [Italiano](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/docs/it/OVERVIEW.md) · [License](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/LICENSE)

---

# E5577 Control v1.0.1 — Italiano

Questa release sostituisce la v1.0.0 e aggiunge la licenza **GPL-3.0-or-later**, gli avvisi su Qt/PySide6 e gli asset legali nei quattro pacchetti. Nessuna modifica funzionale intenzionale al modem o alla UI già approvata. Dopo la conferma della nuova pubblicazione, la precedente GitHub Release v1.0.0 e i suoi installer saranno ritirati, conservandone il tag e la storia Git.

I pacchetti Linux/Windows restano **non firmati**. Le operazioni LTE possono interrompere la rete e i test CI non equivalgono al collaudo fisico.

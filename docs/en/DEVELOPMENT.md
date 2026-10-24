# Development and verification — EN

[Italiano](../it/DEVELOPMENT.md) · [Architecture](ARCHITECTURE.md)

## Local-first setup

On Linux with Python 3.12 and `uv`:

```bash
git clone https://github.com/matteodurso88/e5577-control.git
cd e5577-control
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Develop on `work/*` branches, run local tests and an interactive GUI preview, then open a PR into `main`. Do not mutate actual LTE configuration as part of automated tests. Use a real modem only for separately authorized manual gates. Local `.venv/`, `build/`, `dist/` and user profiles are not release source.

## Test and build gates

`scripts/local_gate.py` compiles the Python package and runs `unittest discover -s tests -v`, including Qt offscreen UI smoke. Tests must exit zero, not just print OK before a native crash. On CI both Linux and Windows run the same tests, then build PyInstaller onedir packages with native installer and portable archive. Linux needs Qt system libraries and `dpkg-deb`; Windows CI installs Inno Setup 6. Packaging dependencies are pinned in CI (`pyinstaller==6.16.0`, `pillow==11.3.0`).

```bash
python -m pip install -e . "pyinstaller==6.16.0" "pillow==11.3.0"
QT_QPA_PLATFORM=offscreen python scripts/local_gate.py
QT_QPA_PLATFORM=offscreen python scripts/build_desktop.py
```

The frozen executable runs `--version` and `--self-check` after building; the latter verifies the runtime imports **and bundled matt88.it SVGs** without contacting a modem or opening the GUI.

## Quality and safety

- New UI elements: stable `objectName`, accessibility names/tooltips, offscreen tests, no incidental Internet or modem traffic.
- For LTE writes: mock behavior in tests, retain read-back and rollback warnings, fail closed when route or hardware support cannot be demonstrated.
- Keep local profiles and OS vault names backward-compatible unless a migration is explicitly tested.
- Do not commit secrets, real private API captures, messages or unredacted device identifiers.
- Changes to the brand artwork must originate in the canonical matt88.it asset source, not an independently redrawn lookalike.

## Releases

Do not publish a release from a PR, old CI artifact or unreviewed working tree. Consult the bilingual [Release runbook](RELEASE.md) and [security policy](SECURITY.md).

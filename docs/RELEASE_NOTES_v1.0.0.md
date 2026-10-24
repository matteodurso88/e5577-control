# E5577 Control v1.0.0 — release candidate notes

**Status: candidate, NOT published.**

This milestone graduates the original Pocket Radio Manager v0.1.0 WORKSHOP prototype to the standalone **E5577 Control** Product, prioritizing Huawei E5577Cs-321. No unverified new modem capabilities are claimed.

## Changes
- App title **E5577 Control · v1.0.0**, persistent footer with `matt88.it` credit, native clickable `https://matt88.it` link, and **Informazioni** dialog with Product name, version, hardware, and publisher.
- Python package metadata and CLI distribution renamed to `e5577-control` (legacy `pocket-radio-manager` command remains as an alias).
- Executable `E5577Control` / `E5577Control.exe`, Linux menu shortcut, Debian package ID `e5577-control` and Windows Inno Setup identity/UI.
- Original vector icon artwork preserved under `assets/e5577-control-icon.svg` and rendered as E5577-branded PNG/ICO.
- Packaging tests and Qt offscreen tests for version, credits and About dialog.
- Profile directory, Python import namespace and OS credential service identifiers intentionally unchanged to preserve user data.

## Required before publication
- [ ] Linux + Windows GitHub Actions tests and builds pass on the exact candidate commit
- [ ] Real-device read-only smoke with Huawei E5577Cs-321
- [ ] Linux/Windows installation, menu entry, About dialog, launch and uninstall smoke
- [ ] Document limitations, code-signing/unsigned warning and SHA256SUMS for final artifacts
- [ ] Explicit approval and annotated v1.0.0 Product tag / release; no auto-publish

## Historical evidence
The original [WORKSHOP v0.1.0](https://github.com/matteodurso88/workshop/releases/tag/pocket-radio-manager/v0.1.0) with four packages and checksums remains unchanged. The Product inherited its complete 124-commit subtree history. See [WORKSHOP_PROVENANCE.md](WORKSHOP_PROVENANCE.md).

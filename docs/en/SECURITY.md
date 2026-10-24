# Security and privacy — EN

[Italiano](../it/SECURITY.md) · [Home](../../README.md)

## Local-only trust boundary

E5577 Control connects to a Huawei modem on a local private/link-local IPv4 address through its compatible HTTP API. No application-specific cloud service or inbound server is required. Network benchmarking, only when explicitly started, generates outside Internet traffic through the selected WAN path.

The saved profile JSON contains device aliases, IP addresses, usernames and optional model metadata — **not passwords**. Password storage is optional and only uses protected OS credential services (Linux Secret Service/KWallet, Windows Credential Manager, supported macOS keyring); unsupported/plaintext backends fail closed. The legacy profile path `pocket-radio-manager` and vault service `io.matt88.pocket-radio-manager` remain intact to avoid losing existing saved secrets.

## Safety boundaries

- Device discovery is constrained to a small set of local candidates; it is not a public-network scanning tool.
- Avoid exposing credentials, Huawei session cookies/tokens, IMEI/serial or message content in logs and support materials.
- SMS are treated as **untrusted plain text**, including in the full-message reader; the app does not send, delete, mark read or automatically export SMS.
- Radio configuration writes require explicit UI actions and should read back changes; firmware may ignore masks, reject operations or become unreachable before restore.
- Band comparison checks the actual IPv4 route to its Internet test endpoint before changing LTE configuration; it may consume mobile data and cause service interruption. Keep alternative Internet access available.
- The UI must distinguish unavailable radio metrics from zero, and permitted-band masks from real serving-cell measurements.

## Packaging and supply chain

Desktop packages are **unsigned**; GitHub Release assets should include SHA-256 checksums. Never trust a binary only because Windows SmartScreen or the desktop warning can be bypassed. Build only from the tagged source with the Linux/Windows GitHub Actions jobs, PyInstaller `--self-check`, and the bundled canonical matt88.it light/dark SVG files. The release workflow must not publish an asset from another commit or silently overwrite an existing release.

Repository access/history may be public. Do not commit real credentials, personal router dumps, SMS, user data, private keys or profiles. Automated secret scanning on the original 124-commit migrated subtree returned no findings, but this is not a comprehensive security guarantee.

## Reporting

Report a vulnerability privately to the maintainer rather than opening an issue containing exploits with active credentials, sensitive logs or personal data. Public non-sensitive bugs: [GitHub Issues](https://github.com/matteodurso88/e5577-control/issues).

Historical source provenance: [WORKSHOP_PROVENANCE.md](../WORKSHOP_PROVENANCE.md).

## License boundaries

E5577 Control code is distributed under GPL-3.0-or-later, with complete terms in the root `LICENSE`. Qt/PySide6 may be distributed under LGPLv3/GPL alternatives depending on the library module; see `LICENSES/LGPL-3.0-only.txt` and `THIRD_PARTY_NOTICES.md`. The full matt88.it visual brand is reserved separately under `NOTICE`, without limiting source-code rights. Version-specific downstream dependencies and LGPL compliance remain the distributor's responsibility.

# Desktop builds — EN / IT

- **English:** [Installation and upgrades](en/INSTALL.md), [Release procedure](en/RELEASE.md), [Development](en/DEVELOPMENT.md).
- **Italiano:** [Installazione e aggiornamenti](it/INSTALL.md), [Procedura di rilascio](it/RELEASE.md), [Sviluppo](it/DEVELOPMENT.md).

E5577 Control v1.0.1 targets Linux x86-64 and Windows x86-64. Each OS build creates a native installer and a portable archive; the tagged workflow publishes the four packages with SHA-256 checksums **only when the release gate succeeds**. Artifacts are unsigned. The original WORKSHOP v0.1.0 packages remain preserved as historical evidence.

[GitHub Releases](https://github.com/matteodurso88/e5577-control/releases) · [Migration provenance](WORKSHOP_PROVENANCE.md)

**Licensing:** Application source GPL-3.0-or-later, with `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` and LGPLv3 text embedded in every v1.0.1 package. After the new release is verified, the older Product GitHub Release v1.0.0 and its binaries will be retired; its historical tag remains.

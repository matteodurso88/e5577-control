# v1.0.0 release procedure — EN

[Italiano](../it/RELEASE.md) · [Development](DEVELOPMENT.md)

## Release contract

**One immutable annotated Git tag, one two-platform CI run, four binaries and one checksum manifest.** Never distribute old PR artifacts under the final version. The release job rebuilds the exact `v1.0.0` tagged commit natively on Ubuntu 24.04 and Windows 2022, runs the offline test suite and frozen `--version` / `--self-check`, then publishes only when both jobs pass.

Release assets:
- `e5577-control-v1.0.0-linux-x86_64.deb`
- `e5577-control-v1.0.0-linux-x86_64.tar.gz`
- `e5577-control-v1.0.0-windows-x86_64-setup.exe`
- `e5577-control-v1.0.0-windows-x86_64.zip`
- `SHA256SUMS.txt` for these four binaries, generated from the release-run output.

## Gates before tagging

1. Merge the `work/v1.0.0-product-ui` PR into `main`, once both OS build jobs pass.
2. Verify the merged `main` commit and associated CI are green.
3. Check the UI, footer SVG, About dialog, offline tests, and that branding SVGs are inside both frozen executables.
4. Confirm signed-off documentation in `docs/en/` and `docs/it/`, the release notes, hardware limitations, and unsigned binary warning.
5. Tag precisely the reviewed current `main` HEAD; do not move or force-push the tag.

## Creating the release

**Approved v1.0.0 publication path:** merge the verified v1.0.0 Product PR to `main` using the exact merge-commit title `release: E5577 Control v1.0.0`. The CI on that exact main commit first executes both native build jobs. Only after both pass, the gated release job creates or verifies annotated tag `v1.0.0`, validates it points to that same commit, assembles the four new binaries, computes `SHA256SUMS.txt` and creates the public GitHub Release. It fails rather than replacing an existing tag/release. A normal `main` push does **not** publish a release. The special merge-commit title constitutes the owner's one-time release authorization.

**Manual tag alternative** (for recovery only, when no release tag exists): from a clean, current local `main` checkout with an authenticated `gh` CLI:

```bash
git fetch origin main --tags
git switch main
git pull --ff-only origin main
git status --short
git tag -a v1.0.0 -m "E5577 Control v1.0.0"
git push origin refs/tags/v1.0.0
```

Only run after verifying `git status --short` has no tracked changes and that `v1.0.0` does not already exist. A tag push triggers `.github/workflows/e5577-control-desktop.yml`: two fresh native builds followed by a guarded release job. The workflow fails rather than overwriting an existing release. Review the final release URL and the workflow logs; tagging by itself is **not** proof of a published release.

## Verification after publication

Download assets from the published [v1.0.0 release](https://github.com/matteodurso88/e5577-control/releases/tag/v1.0.0). Run `sha256sum -c SHA256SUMS.txt` on Linux or `Get-FileHash` on Windows and compare all hashes. Confirm each binary's version, installer/portable launch and uninstall behavior. Record any outstanding physical-modem or Windows GUI acceptance separately; a CI unit test does not prove hardware behavior. Do not modify the release tag after publication.

The original WORKSHOP v0.1.0 release and source history remain preserved separately.

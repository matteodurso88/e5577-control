# E5577 Control — WORKSHOP provenance and migration ledger

## Product identity

- Product name: **E5577 Control**
- Canonical Product repository: [matteodurso88/e5577-control](https://github.com/matteodurso88/e5577-control)
- WORKSHOP technical origin: `matteodurso88/workshop/pocket-manager/` (private repository)
- Hardware priority: **Huawei E5577Cs-321**; do not claim broader hardware compatibility without testing.
- Promotion decision: 2026-10-24 (explicit owner decision)

## Git history preserved

E5577 Control's initial `main` was created by extracting **only** the `pocket-manager/` subtree with:

```sh
git subtree split --prefix=pocket-manager <workshop-main-commit>
```

This preserves the sequence and content of the 124 relevant subtree commits, with original author identities, dates, and commit messages, while placing the app at the **repository root**. Subtree commit IDs differ from the WORKSHOP original commits because their trees/parent links are rewritten.

- Initial Product main: `9e312eeec84f2fe257db4d00c41d8f83653d836f`
- First subtree commit: `f5072f9`
- Last WORKSHOP commit affecting subtree before extraction: `405fae60669209a0a05a2147ff092f49053580af`
- WORKSHOP main at audit: `679e44a777ebfcf110dbc0817833e934a1fd5af3`
- Integrity check: `subtree_split^{tree}` equals `workshop/main:pocket-manager` (**PASS**).
- History count: **124 commits**, both before and after push; remote head exactly matched.
- Detached Git backup: full `git bundle` verified locally by the owner.
- Security pre-publication audit: Gitleaks scanned all 124 commits; exit code 0, no leaks found. This is not a complete privacy guarantee.

**No other WORKSHOP projects, branches, or tags were imported into the Product history.**

## History retained in WORKSHOP (not transferable via subtree split)

The WORKSHOP source repository remains intact as the historical origin and reference for:

- Merged [WORKSHOP PR #18](https://github.com/matteodurso88/workshop/pull/18) (merge commit `a5b0af348154ac9bc261cc25ddea4031d8fff0e2`).
- Original WORKSHOP [Issue #17](https://github.com/matteodurso88/workshop/issues/17).
- Original WORKSHOP [release pocket-radio-manager/v0.1.0](https://github.com/matteodurso88/workshop/releases/tag/pocket-radio-manager/v0.1.0).
- Four native Linux/Windows packages and `SHA256SUMS.txt` attached to that original release.
- GitHub Actions runs, logs, artifacts, and the original workflow outside the subtree: `.github/workflows/pocket-radio-manager-desktop.yml`.

The history of this workflow itself remains in WORKSHOP, including commits `97fdd41`, `ea4f095`, `2eba92b`; these cannot be represented as original subtree commits because they modified files outside `pocket-manager/`. The workflow has been ported to the Product repository root separately, with its WORKSHOP provenance noted here.

## Product publication and source retirement

- Imported historical version: `0.1.0` (*Pocket Radio Manager*). Version `1.0.0` is the separate standalone **E5577 Control** Product milestone.
- The Product identity, executable, Linux desktop package and Windows installer are now branded **E5577 Control**, with the canonical complete `matt88.it` SVG wordmark in the compact GUI footer.
- Legacy local profile storage and keyring service identifiers were **deliberately retained** to protect existing saved device credentials.
- The original WORKSHOP `pocket-manager/` subtree and obsolete workflow were removed from the **current main tree** in [WORKSHOP PR #22](https://github.com/matteodurso88/workshop/pull/22), merged at `5307294af6df83d2d538289da922196acb40f30c`. They remain retrievable from WORKSHOP Git history, without any history rewrite, tag or release deletion.
- The original WORKSHOP release assets are accessible to authorized viewers of the private source repository; they are **not republished or relabeled** as Product binaries.
- Standalone CI builds native Linux/Windows packages. A new `v1.0.0` **annotated Git tag** starts fresh two-platform builds and gated publication of four packages with `SHA256SUMS.txt`. A release must not overwrite an existing publication.
- Release truth is the [Product Releases page](https://github.com/matteodurso88/e5577-control/releases), not a claim in a historical document. See [English](en/RELEASE.md) and [Italiano](it/RELEASE.md) runbooks.

## Completion tracking

See [Product migration Issue #1](https://github.com/matteodurso88/e5577-control/issues/1) for the verified migration and outstanding release gates. WORKSHOP retains its immutable history and original GitHub objects.

## v1.0.1 GPL licensing update (2026-10-24)

The initial standalone v1.0.0 GitHub Release was published on commit `dbe5192da597c84e690d0e96e3d62c1fffdb2dc3` without an explicit root LICENSE. The owner subsequently selected `GPL-3.0-or-later` for E5577 Control source and authorized the v1.0.1 license-correction release. This changes current source licensing metadata without rewriting prior commit contents. The new v1.0.1 release embeds the full license and notices in all four packages, and withdraws the previously published v1.0.0 GitHub Release assets **only after** successful validation of the replacement. The annotated v1.0.0 Git tag and original source commit remain intact as provenance, alongside the older private WORKSHOP v0.1.0 release.

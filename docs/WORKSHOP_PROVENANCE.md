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

## Release policy / status

- Source version at import: `0.1.0` (formerly *Pocket Radio Manager*).
- **The Product has NOT yet published a native E5577 Control release.**
- Existing source code, desktop binary names, packaging IDs, and historic documentation may still use *Pocket Radio Manager* pending the controlled rebrand and fresh platform packaging QA.
- WORKSHOP release assets are historical and remain available to people authorized to view that private source repository; they are **not silently republished or relabeled** as Product builds.
- Product CI builds Linux/Windows candidate artifacts on PR/main. A Product GitHub Release requires a **separate, explicit publication gate**, after branding, test verification, package integrity, and owner acceptance.
- Never overwrite or retag the immutable historical WORKSHOP release.

## Completion tracking

See [Product migration Issue #1](https://github.com/matteodurso88/e5577-control/issues/1) for current migration gates. Do not remove source subtree or retire WORKSHOP references until the Product migration and verification have completed.

# matt88.it canonical logo in E5577 Control

Source of truth: the private website repository `matteodurso88/matt88`,
`public/brand/matt88/logo-light.svg` and `logo-dark.svg` at 2026-10-24.
Brand guideline: `docs/brand/logo-guidelines.md` (wordmark is symbol plus
`matt88.it`; do not use just the symbol in a horizontal footer).

This Product vendors byte-identical copies at:

- `assets/matt88/logo-light.svg` for light Qt surfaces (dark wordmark).
- `assets/matt88/logo-dark.svg` for dark Qt surfaces (light wordmark).

The footer replaces the former text credit with a **clickable 18px-tall
complete brand wordmark** linking to `https://matt88.it`. The 22px footer
row and 20px icon button preserve the compact layout. Theme selection uses
the Qt window palette and is updated on palette change, without requiring
external downloads or modifying the canonical SVG files.

The About dialog still provides a textual credit for clarity/accessibility.
Both SVGs are bundled with PyInstaller and asserted by the frozen
`--self-check`, so Linux/Windows installers work without network access.

Brand ownership: matt88.it (Matteo D'Urso).
Changing the SVG artwork itself requires separate owner approval.

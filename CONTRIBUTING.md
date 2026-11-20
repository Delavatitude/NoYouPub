# Contributing / Contribuer

This repository is a local V3 preparation. A project license and contributor/publication policy must be approved before soliciting public contributions. Do not assume permission to redistribute simply because source files exist.

Use a dedicated branch and a separate development data directory and Chrome profile. Preserve 2.5 media behaviors and state formats; avoid unnecessary architecture rewrites. Never edit the installed application, its runtime or personal configuration to run tests. Do not add live TV/YouTube fixtures or signed media URLs to the repository.

Use the isolated environment in `docs/BUILD.md`. Run `scripts/test_all.py --swift`, the focused synthetic codec check when changing media processing, locale generation and the public-tree audit. Record platform, actual passes/failures and untested hardware. A mocked TV is not a hardware validation. Keep regression tests attached to externally meaningful behavior rather than rechecking implementation text.

For localization, edit shared FR/EN catalogs and preserve interpolation placeholders. Generate Chrome catalogs; do not hand-edit generated messages. Mark provider titles as content, not translatable interface text. Add tests before advertising a new language.

Review changes for origin validation, command bounds, local server exposure, state ownership, cancellation and cleanup. PR descriptions should state the concrete behavior, validation and remaining limits. Do not enable an automatic publishing workflow, push a branch, sign for distribution or upload a release without the owner's explicit approval.

Français : documenter les changements et tests, préserver tous les contrôles/file/navigation, utiliser des données synthétiques et demander l’accord du responsable avant toute diffusion publique. La branche actuelle ne change pas la licence du travail initial.

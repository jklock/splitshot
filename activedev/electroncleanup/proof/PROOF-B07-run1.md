# B07 — Build pipeline all 3 platforms

## Status: Complete

## Changes

- `scripts/bundle-python.js`: Complete rewrite
  - Detects Python version dynamically instead of hardcoding 3.12
  - Resolves uv symlinks more robustly
  - Generates icons in `electron/assets/` instead of `electron/build/`
  - Verification step tests `--headless`-mode imports
  - Supports `check` mode (verify without rebuild)
  - All pruning logic preserved (PySide6, numpy, etc.)

- `electron/package.json`: Added `bundle` script

- `.github/workflows/build-electron.yml`: Complete rewrite
  - Single bundling per platform (no duplication)
  - Linux: installs system deps (ffmpeg, Qt libs)
  - Runs `uv run splitshot --check` and parity audit
  - Verifies bundle integrity
  - Verifies installer after build
  - Clean step organization

## Verification

```bash
npm --prefix electron run bundle
npm --prefix electron run check
npm --prefix electron run build:mac  # or :win, :linux
```

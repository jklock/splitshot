# B01 — Delete root main.js + organize assets

## Status: Complete

## Changes

- `./main.js`: **Deleted** (root-level duplicate of `electron/main.js`)
- `electron/assets/`: Created with `.gitkeep`
- `electron/package.json`:
  - `mac.icon`: `build/icon.icns` → `assets/icon.icns`
  - `win.icon`: `build/icon.ico` → `assets/icon.ico`
  - `linux.icon`: `build/icon.png` → `assets/icon.png`
- `.gitignore`: Already had `electron/bundle/`, `electron/build/`, `electron/node_modules/` — no changes needed

## Verification

```bash
ls electron/assets/.gitkeep
git diff --stat  # confirm no unintended changes
```

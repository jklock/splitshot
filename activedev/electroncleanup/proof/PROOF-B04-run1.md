# B04 — Application menu

## Status: Complete

## Changes

- `electron/main.js`: Added `buildAppMenu()` function with:
  - macOS app menu (About, Hide, Quit)
  - File menu (Open Project..., Close/Quit)
  - Edit menu (Undo, Redo, Cut, Copy, Paste, Select All)
  - View menu (Reload, DevTools, Zoom, Fullscreen)
  - Window menu (Minimize, Zoom, etc.)
  - Help menu (Website, Report Issue)

## Verification

```bash
npm --prefix electron run dev
# Expected: native menu bar with all menus
```

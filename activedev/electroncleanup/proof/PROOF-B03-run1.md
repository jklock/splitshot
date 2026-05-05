# B03 — IPC bridge

## Status: Complete

## Changes

- `electron/main.js`: Added IPC handlers:
  - `get-version` — returns app version
  - `get-platform` — returns `process.platform`
  - `open-file` — native file open dialog (video + project files)
  - `open-project-dialog` — native project file open dialog
- `electron/preload.js`: Exposes all IPC channels:
  - `getVersion`, `getPlatform`, `openFile`, `openProjectDialog`, `onOpenProject`

## Verification

All IPC methods have corresponding handlers. No dead/broken code in preload.

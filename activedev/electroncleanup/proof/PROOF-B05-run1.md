# B05 — File associations all 3 platforms

## Status: Complete

## Changes

- `electron/package.json`:
  - Removed `backend.py` from `extraResources` (no longer needed)
  - Added `mimeType` to `fileAssociations` for Linux
  - Added Linux-specific `mimeTypes` and `desktop.MimeType`
  - macOS `CFBundleDocumentTypes` already configured
  - Windows `.ssproj` handled via `fileAssociations`
  - `splitshot://` protocol handler already configured

## Verification

```bash
# macOS
npm --prefix electron run build:mac
# Expected: double-click .ssproj opens SplitShot

# Windows/Linux
npm --prefix electron run build:win
npm --prefix electron run build:linux
```

# E03 — Production Build

## Metadata

| Field | Value |
| --- | --- |
| task-id | `E03` |
| status | `pending` |
| depends-on | `E01`, `E02` |
| risk | `medium` |
| touches-files | `electron/package.json`, `electron/build/`, `activedev/electron/progress.md` |
| forbidden-files | `src/`, `pyproject.toml` |
| proof-file | `activedev/electron/proof/PROOF-E03-runN.md` |

## Goal

Configure electron-builder for production-quality installers on all three platforms, generate app icons from the existing logo, and produce the distributable `.dmg`/`.exe`/`.AppImage`.

## Implementation

### 1. App icons

Generate platform-specific icons from `src/splitshot/browser/static/logo.png`:

```bash
# macOS: .icns
mkdir -p electron/build/icons.iconset
for size in 16 32 64 128 256 512 1024; do
  sips -z $size $size logo.png --out "electron/build/icons.iconset/icon_${size}x${size}.png"
  [ $size -le 512 ] && sips -z $((size*2)) $((size*2)) logo.png --out "electron/build/icons.iconset/icon_${size}x${size}@2x.png"
done
iconutil -c icns electron/build/icons.iconset -o electron/build/icon.icns

# Windows: .ico (requires ImageMagick or similar)
convert electron/build/icon.png -define icon:auto-resize=256,64,48,32,16 electron/build/icon.ico

# Linux: .png
cp electron/build/icon.png electron/build/icon.png
```

### 2. electron-builder config

Already defined in `electron/package.json` from E01. Verify the following:

- `extraResources` correctly points to `electron/bundle/` → `bundle/`
- macOS `hardenedRuntime` is enabled
- File associations for `.ssproj` are registered
- `protocols` for `splitshot://` deep links are configured

### 3. Build and test

```bash
# macOS
npm --prefix electron run build:mac
open electron/build/SplitShot.dmg

# Windows (cross-compile from macOS not possible without CI)
# npm --prefix electron run build:win

# Linux (cross-compile)
# npm --prefix electron run build:linux
```

### 4. macOS notarization (optional)

If signing with an Apple Developer account:

```bash
# After build, notarize the dmg
xcrun notarytool submit electron/build/SplitShot.dmg \
  --apple-id "$APPLE_ID" \
  --team-id "$TEAM_ID" \
  --password "$APP_PASSWORD" \
  --wait
```

## Validation

```bash
npm --prefix electron run build:mac
# Expected: electron/build/SplitShot.dmg exists
# Manual: install the dmg, open the app, verify:
#   - App launches without terminal
#   - Import/analyze/export works
#   - .ssproj double-click opens the project
```

## Done criteria

- [ ] App icons generated for all platforms
- [ ] `npm run build:mac` produces a working `.dmg`
- [ ] Installed app launches and runs full workflow
- [ ] `.ssproj` file association works (double-click opens project)
- [ ] Dev workflow (`uv run splitshot`) still works
- [ ] Proof written, progress updated

# B05 — File associations (macOS, Windows, Linux)

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B05` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `B02` |
| risk | `medium` |
| touches-files | `electron/main.js`, `electron/package.json` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B05-runN.md` |

## Goal

Users can double-click a `.ssproj` file in Finder / Explorer / file manager
and the project opens in SplitShot. `.ssproj` files get the correct icon,
description, and MIME type on all three platforms.

## Background

`electron/package.json` already has `fileAssociations` and
`CFBundleDocumentTypes` configured. But:
1. macOS `open-file` event handler in `main.js` is missing
2. `protocols` config for `splitshot://` deep links is untested
3. Windows file open via argv handler is missing
4. **Linux MIME registration is unverified** — electron-builder generates
   `.desktop` files from `fileAssociations`, but we must verify the output.

## Implementation

### 1. `electron/package.json` — verify cross-platform file assoc config

The current config:
```json
"fileAssociations": [
  {
    "ext": "ssproj",
    "name": "SplitShot Project",
    "description": "SplitShot project bundle",
    "role": "Editor"
  }
],
"protocols": {
  "name": "SplitShot",
  "schemes": ["splitshot"]
}
```

**macOS**: `role: "Editor"` maps to `CFBundleTypeRole`. This is correct.
**Windows**: NSIS installer registers the extension. This is correct.
**Linux**: electron-builder generates:
- `~/.local/share/mime/packages/studio.splitshot.app-ssproj.xml`
- Updates `~/.local/share/applications/splitshot.desktop` with MimeType

**Verify Linux MIME XML output** by building and checking:
```bash
npm run build:linux
# Inspect the generated AppImage's .desktop file
# It should contain: MimeType=application/x-studio.splitshot.ssproj;
```

If the MIME type isn't generated correctly, add a custom MIME XML
file at `electron/assets/ssproj-mime.xml`:

```xml
<?xml version="1.0"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-studio.splitshot.ssproj">
    <comment>SplitShot Project</comment>
    <glob pattern="*.ssproj"/>
  </mime-type>
</mime-info>
```

### 2. `electron/main.js` — macOS `open-file` handler

```javascript
// macOS: double-click on .ssproj file or any associated file
app.on('open-file', (event, filePath) => {
  event.preventDefault();
  if (mainWindow) {
    const ext = path.extname(filePath).toLowerCase();
    const channel = ext === '.ssproj' ? 'open-project-event' : 'open-file-event';
    mainWindow.webContents.send(channel, filePath);
    mainWindow.focus();
  } else {
    app.pendingProjectPath = filePath;
  }
});
```

### 3. `electron/main.js` — Windows/Linux file open via argv

```javascript
// Process command-line arguments (Windows file association, Linux desktop)
const pendingFilePath = process.argv.find(
  (arg) => arg.endsWith('.ssproj') && arg !== process.execPath
);
if (pendingFilePath) {
  app.whenReady().then(() => {
    const checkWindow = setInterval(() => {
      if (mainWindow) {
        clearInterval(checkWindow);
        mainWindow.webContents.send('open-project-event', pendingFilePath);
      }
    }, 200);
  });
}
```

### 4. Handle `pendingProjectPath` in `createWindow()`

```javascript
function createWindow() {
  // ... existing window creation ...
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (app.pendingProjectPath) {
      mainWindow.webContents.send('open-project-event', app.pendingProjectPath);
      app.pendingProjectPath = null;
    }
  });
}
```

### 5. Deep links — `splitshot://` protocol (all platforms)

```javascript
app.setAsDefaultProtocolClient('splitshot');

app.on('open-url', (event, url) => {
  event.preventDefault();
  try {
    const parsed = new URL(url);
    if (parsed.pathname === '/open' || parsed.pathname === 'open') {
      const filePath = parsed.searchParams.get('path');
      if (filePath && mainWindow) {
        mainWindow.webContents.send('open-project-event', filePath);
      }
    }
  } catch (err) {
    console.error('Failed to parse deep link:', err);
  }
});
```

### 6. Verify `.ssproj` icon on each platform

**macOS**: Icon set by `.icns` in `electron/assets/`. The
`CFBundleDocumentTypes.LSHandlerRank: "Owner"` config ensures SplitShot
is the default handler.

```bash
# After install, refresh LaunchServices
/System/Library/Frameworks/CoreServices.framework/Frameworks/\
  LaunchServices.framework/Support/lsregister -kill
```

**Windows**: Icon set via NSIS installer. electron-builder handles this
when `icon` is configured in `win` target. No manual steps.

**Linux**: Icon set in `.desktop` file. electron-builder copies
`build/icon.png` (now `assets/icon.png`) to the AppImage resources.
After install:
```bash
# Update MIME database
update-mime-database ~/.local/share/mime
# Update desktop database
update-desktop-database ~/.local/share/applications
```

## Validation

```bash
# macOS
npm --prefix electron run build:mac
open electron/build/SplitShot.dmg
# Drag to Applications, launch once

mkdir -p /tmp/test-project
echo '{"version":"1.0"}' > /tmp/test-project/project.json
ln -s /tmp/test-project ~/Desktop/test.ssproj
# Double-click test.ssproj in Finder
# Expected: SplitShot opens with the project loaded
open "splitshot://open?path=/tmp/test-project"
# Expected: SplitShot opens with the project

# Windows
npm --prefix electron run build:win
# Run the installer, check .ssproj file association in Settings > Apps > Default Apps
# Double-click .ssproj → SplitShot opens

# Linux
npm --prefix electron run build:linux
# Inspect generated MIME XML
ls ~/.local/share/mime/packages/*ssproj*
grep -r "ssproj" ~/.local/share/applications/
# Expected: MIME type and .desktop entry exist
# Launch .AppImage with a .ssproj argument
./SplitShot-*.AppImage /path/to/project.ssproj
# Expected: SplitShot opens with the project
```

## Done criteria

- [ ] macOS: double-click `.ssproj` opens project in SplitShot
- [ ] macOS: `open-file` event handler forwards path to renderer
- [ ] Windows: `.ssproj` file association registered by installer
- [ ] Linux: FreeDesktop MIME XML generated for `.ssproj`
- [ ] Linux: `.desktop` file has correct MimeType entry
- [ ] Linux: `.AppImage` launched with `.ssproj` arg opens the project
- [ ] Deep link handler for `splitshot://` protocol (all platforms)
- [ ] Pending file path handled when app launches via file open
- [ ] `.ssproj` has correct icon in Finder / Explorer / file manager
- [ ] Verification commands documented for all three platforms
- [ ] Proof written, progress updated

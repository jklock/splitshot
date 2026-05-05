# B03 — IPC bridge completeness

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B03` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `B02` |
| risk | `medium` |
| touches-files | `electron/main.js`, `electron/preload.js` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B03-runN.md` |

## Goal

Wire every method in the `window.splitshot` preload bridge to a working
IPC handler. The bridge must be minimal, documented, and every method
must have a corresponding handler in `main.js`.

## Background

Current preload exposes 5 methods but only 2 have handlers:
- `getVersion()` → handler exists ✓
- `getPlatform()` → NO handler ✗
- `openFile()` → handler exists but result goes nowhere ✗
- `openProject(path)` → NO handler ✗
- `onOpenProject(callback)` → NO handler ✗

This is dead/broken code. The user's page cannot receive dialog results
or file-open events.

## Implementation

### 1. Define the IPC surface

| Method | Trigger | Returns | Notes |
|--------|---------|---------|-------|
| `getVersion()` | `ipcRenderer.invoke('get-version')` | `string` | Already works |
| `getPlatform()` | `ipcRenderer.invoke('get-platform')` | `string` | `process.platform` |
| `openFile(type)` | `ipcRenderer.invoke('open-file', type)` | `string \| null` | `type`: `'video'` or `'project'`, returns path or null |
| `onOpenFile(callback)` | `ipcRenderer.on('open-file-event', callback)` | `void` | Receives file path from macOS events |
| `onOpenProject(callback)` | `ipcRenderer.on('open-project-event', callback)` | `void` | Receives `.ssproj` path |

### 2. `electron/main.js` — add handlers

```javascript
ipcMain.handle('get-version', () => app.getVersion());

ipcMain.handle('get-platform', () => process.platform);

ipcMain.handle('open-file', async (_event, type) => {
  const filters = type === 'project'
    ? [{ name: 'SplitShot Projects', extensions: ['ssproj'] }]
    : [{ name: 'Videos', extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'] }];
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters,
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.on('open-file-event', (_event, filePath) => {
  // Forward to renderer
  if (mainWindow) {
    mainWindow.webContents.send('open-file-event', filePath);
  }
});
```

### 3. `electron/preload.js` — wire the bridge

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splitshot', {
  getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  openFile: (type) => ipcRenderer.invoke('open-file', type),
  onOpenFile: (callback) => {
    ipcRenderer.on('open-file-event', (_event, path) => callback(path));
  },
  onOpenProject: (callback) => {
    ipcRenderer.on('open-project-event', (_event, path) => callback(path));
  },
});
```

### 4. Remove stale `preload.js` methods

The old preload had `openProject(path)` which tried to invoke an
`open-project` IPC — but Electron handles file opening via OS events,
not by the renderer pushing paths. The correct pattern is:
- Renderer calls `splitshot.openFile('project')` to open dialog
- OS sends open-file events which main.js forwards via `onOpenProject`
- Main process can also send file paths when Electron receives
  `open-file` from macOS

### 5. Add `open-file` macOS handler in `electron/main.js`

Already planned in B05, but add the basic wiring:
```javascript
app.on('open-file', (_event, filePath) => {
  _event.preventDefault();
  if (mainWindow) {
    const ext = path.extname(filePath).toLowerCase();
    const channel = ext === '.ssproj' ? 'open-project-event' : 'open-file-event';
    mainWindow.webContents.send(channel, filePath);
  }
});
```

## Validation

```javascript
// Run this in Electron devtools console:
const v = await window.splitshot.getVersion();
console.assert(typeof v === 'string', 'getVersion() returns string');

const p = await window.splitshot.getPlatform();
console.assert(typeof p === 'string', 'getPlatform() returns string');

// These should trigger native dialogs (manual verification)
const videoPath = await window.splitshot.openFile('video');
console.log('Selected:', videoPath);

const projPath = await window.splitshot.openFile('project');
console.log('Selected:', projPath);
```

## Done criteria

- [ ] Every `preload.js` method has a corresponding IPC handler
- [ ] `openFile(type)` opens correct dialog filter
- [ ] macOS `open-file` event forwarded to renderer
- [ ] No stale/unused IPC handlers
- [ ] Preload surface is minimal and documented
- [ ] Proof written, progress updated

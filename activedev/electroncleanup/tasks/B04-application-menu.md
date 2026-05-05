# B04 — Application menu

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B04` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `B02` |
| risk | `medium` |
| touches-files | `electron/main.js` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B04-runN.md` |

## Goal

Add a complete native application menu so the Electron app feels like a
real desktop app, not a browser tab. Standard menu items must trigger the
correct SplitShot actions via the web page or native APIs.

## Background

Currently there is no custom menu. Electron's default menu has basic items
but no SplitShot-specific actions (Open Video, Open Project, Export, etc.).

## Implementation

### 1. Build the menu template

Create a `buildApplicationMenu()` function in `electron/main.js`:

```javascript
const { Menu, shell } = require('electron');

function buildApplicationMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    // macOS app menu
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    }] : []),

    // File menu
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Video...',
          accelerator: 'CmdOrCtrl+O',
          click: async () => {
            const path = await handleOpenFile('video');
            if (path && mainWindow) {
              mainWindow.webContents.send('open-file-event', path);
            }
          },
        },
        {
          label: 'Open Project...',
          accelerator: 'CmdOrCtrl+Shift+O',
          click: async () => {
            const path = await handleOpenFile('project');
            if (path && mainWindow) {
              mainWindow.webContents.send('open-project-event', path);
            }
          },
        },
        { type: 'separator' },
        {
          label: 'Save Project',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.executeJavaScript(
                'window.__splitshot_save && window.__splitshot_save()'
              );
            }
          },
        },
        { type: 'separator' },
        ...(isMac ? [{ role: 'close' }] : [{ role: 'quit' }]),
      ],
    },

    // Edit menu
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },

    // View menu
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },

    // Window menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front' },
          { type: 'separator' },
          { role: 'window' },
        ] : [{ role: 'close' }]),
      ],
    },

    // Help menu
    {
      role: 'help',
      submenu: [
        {
          label: 'SplitShot Documentation',
          click: async () => {
            await shell.openExternal('https://splitshot.studio/docs');
          },
        },
        {
          label: 'Report Issue',
          click: async () => {
            await shell.openExternal('https://github.com/your-org/splitshot/issues');
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}
```

### 2. Extract `handleOpenFile` helper

The menu's Open Video/Project callbacks need the same dialog logic as
the IPC handlers. Extract into a shared function:

```javascript
async function handleOpenFile(type) {
  const filters = type === 'project'
    ? [{ name: 'SplitShot Projects', extensions: ['ssproj'] }]
    : [{ name: 'Videos', extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'] }];
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters,
  });
  return result.canceled ? null : result.filePaths[0];
}
```

### 3. Wire IPC handler to shared dialog logic

Update the `open-file` IPC handler to call `handleOpenFile()` so the
dialog logic is not duplicated:

```javascript
ipcMain.handle('open-file', async (_event, type) => {
  return handleOpenFile(type);
});
```

### 4. Install menu on app ready

```javascript
app.on('ready', async () => {
  buildApplicationMenu();
  startPythonBackend();
  // ... rest of startup
});
```

### 5. Save Project via web page

The Save Project menu item uses `executeJavaScript` to call
`window.__splitshot_save()` if it exists. The web page should define
this function to trigger the save API. Add this to the `preload.js`
(wired during B03):

```javascript
// In preload.js — provide a way for the menu to trigger saves
contextBridge.exposeInMainWorld('splitshot', {
  // ... existing methods ...
  onSaveProject: (callback) => {
    window.__splitshot_save = callback;
  },
});
```

## Validation

```bash
# Manual verification
npm --prefix electron run dev

# Verify:
# - All menu items appear
# - Cmd+O opens native video picker
# - Cmd+Shift+O opens project picker
# - Cmd+S triggers save (check console)
# - Edit/View/Window menus work
# - Help > Documentation opens browser
```

## Done criteria

- [ ] File menu: Open Video (Cmd+O), Open Project (Cmd+Shift+O), Save
- [ ] Edit menu: standard undo/redo/cut/copy/paste
- [ ] View menu: reload, zoom, devtools, fullscreen
- [ ] macOS: app menu with About, Hide, Quit
- [ ] Open Video/Project triggers correct native dialog
- [ ] Save Project calls into the web page via `executeJavaScript`
- [ ] No menu duplication on macOS (only one app menu)
- [ ] Proof written, progress updated

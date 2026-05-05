# SplitShot Electron Desktop App

## Goal

Package SplitShot as a native desktop application so non-technical users can download, install, and run it without touching a terminal or installing Python.

## How it works

Electron wraps the existing Python backend + static assets into a single `.app`/`.exe`:

```
User downloads SplitShot.dmg
        │
        ▼
  Double-click → SplitShot.app opens
        │
        ├── Electron window appears
        ├── Spawns python-backend as child process (port 8765)
        ├── Loads http://127.0.0.1:8765 in the Electron BrowserWindow
        ├── User analyzes and exports video
        └── Close window → kills python-backend
```

The user never sees a terminal, never installs Python, never types a command.

## Project structure

```
electron/
├── package.json              # Electron + build config
├── main.js                   # Main process (spawns Python, creates window)
├── preload.js                # Preload script for IPC bridge
└── build/                    # Build output (created by electron-builder)
    └── SplitShot.dmg         # Installable artifact

scripts/bundle-python.js      # Bundles Python + dependencies + FFmpeg into the app
```

## Files to create

### 1. `electron/package.json`

```json
{
  "name": "splitshot",
  "version": "1.1.0",
  "description": "Competition shooting video analysis, scoring, and export",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "node scripts/bundle-python.js && electron-builder",
    "build:mac": "node scripts/bundle-python.js && electron-builder --mac",
    "build:win": "node scripts/bundle-python.js && electron-builder --win",
    "build:linux": "node scripts/bundle-python.js && electron-builder --linux"
  },
  "author": "SplitShot",
  "license": "MIT",
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0"
  },
  "build": {
    "appId": "studio.splitshot.app",
    "productName": "SplitShot",
    "directories": {
      "output": "electron/build"
    },
    "files": [
      "electron/main.js",
      "electron/preload.js",
      "!bundle/**/_internal/PySide6/Qt/plugins/**"
    ],
    "extraResources": [
      {
        "from": "electron/bundle",
        "to": "bundle",
        "filter": ["**/*"]
      }
    ],
    "mac": {
      "category": "public.app-category.sports",
      "target": ["dmg"],
      "icon": "electron/build/icon.icns",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "extendInfo": {
        "CFBundleDocumentTypes": [
          {
            "CFBundleTypeName": "SplitShot Project",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
            "LSItemContentTypes": ["studio.splitshot.ssproj"]
          }
        ]
      }
    },
    "win": {
      "target": ["nsis"],
      "icon": "electron/build/icon.ico"
    },
    "linux": {
      "target": ["AppImage"],
      "icon": "electron/build/icon.png",
      "category": "Sports"
    },
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
  }
}
```

### 2. `electron/main.js`

```javascript
const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let pythonProcess = null;
const PORT = 8765;
const PYTHON_URL = `http://127.0.0.1:${PORT}`;

function getBundlePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'bundle');
  }
  return path.join(__dirname, '..');
}

function getPythonBinary() {
  const bundle = getBundlePath();
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(bundle, '.venv', binDir, `python${ext}`);
}

function getSplitshotModule() {
  return path.join(getBundlePath(), 'src');
}

function startPythonBackend() {
  const python = getPythonBinary();
  const modulePath = getSplitshotModule();

  pythonProcess = spawn(python, [
    '-m', 'splitshot',
    '--web',
    '--host', '127.0.0.1',
    '--port', String(PORT),
    '--no-open',
  ], {
    cwd: getBundlePath(),
    env: {
      ...process.env,
      PYTHONPATH: modulePath,
      SPLITSHOT_ELECTRON: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[python] ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[python] ${data}`);
  });

  pythonProcess.on('exit', (code) => {
    console.log(`Python backend exited with code ${code}`);
    if (!app.isQuitting) {
      app.quit();
    }
  });
}

function waitForServer(retries = 30) {
  return new Promise((resolve, reject) => {
    const tryConnect = (attempt) => {
      if (attempt >= retries) {
        reject(new Error('Python backend failed to start'));
        return;
      }
      const http = require('http');
      const req = http.get(`${PYTHON_URL}/api/state`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(() => tryConnect(attempt + 1), 500);
        }
      });
      req.on('error', () => {
        setTimeout(() => tryConnect(attempt + 1), 500);
      });
      req.end();
    };
    tryConnect(0);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'SplitShot',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  mainWindow.loadURL(PYTHON_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', async () => {
  startPythonBackend();
  try {
    await waitForServer();
    console.log('Python backend is ready');
    createWindow();
  } catch (err) {
    console.error(err);
    dialog.showErrorBox('Startup Error', 'Failed to start the SplitShot backend. Please try reinstalling the application.');
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
});
```

### 3. `electron/preload.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splitshot', {
  getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => process.platform,
  openFile: () => ipcRenderer.invoke('open-file'),
  openProject: (path) => ipcRenderer.invoke('open-project', path),
  onOpenProject: (callback) => ipcRenderer.on('open-project', (_event, path) => callback(path)),
});
```

### 4. `electron/main.js` — IPC handlers (add before createWindow)

```javascript
const { ipcMain } = require('electron');

ipcMain.handle('get-version', () => app.getVersion());

ipcMain.handle('open-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Videos', extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm'] },
      { name: 'SplitShot Projects', extensions: ['ssproj'] },
    ],
  });
  return result.canceled ? null : result.filePaths[0];
});
```

## Python bundling

### `scripts/bundle-python.js`

Purpose: create a self-contained Python runtime inside `electron/bundle/` that includes SplitShot, its dependencies, and FFmpeg.

High-level steps:

```
bundle-python.js:
1. Create electron/bundle/ directory
2. Run: python3 -m venv bundle/.venv
3. Run: bundle/.venv/bin/pip install splitshot[dev] (or pip install . from repo root)
4. Run: bundle/.venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"  → copies ffmpeg binaries
5. Copy src/ to bundle/src/
6. Copy pyproject.toml to bundle/
7. Prune: remove __pycache__, .pyc files, test directories, documentation
8. Result: bundle/ is ~150MB (Python + PySide6 + numpy + FFmpeg)
```

The bundling runs at build time (developer machine), not at install time (user machine).

## Icon generation

Generate from `src/splitshot/browser/static/logo.png`:

| Platform | Format | Sizes |
|----------|--------|-------|
| macOS | `.icns` | 1024x1024 (multi-resolution) |
| Windows | `.ico` | 256x256 |
| Linux | `.png` | 512x512 |

```bash
# Requires iconutil (macOS) or ImageMagick
mkdir -p electron/build
# Generate using the existing logo.png
sips -z 1024 1024 src/splitshot/browser/static/logo.png --out electron/build/icon.png
iconutil -c icns electron/build/icon.icns  # or use png2icns
```

## Build commands

```bash
# Development: run from repo root (requires uv sync --extra dev already done)
npm --prefix electron install
npm --prefix electron run start       # Starts Electron, spawns Python

# Production build (macOS):
node scripts/bundle-python.js         # Creates electron/bundle/ with Python + deps
npm --prefix electron run build:mac   # Produces electron/build/SplitShot.dmg
```

## File associations

`.ssproj` bundles (directories with `project.json`) are registered with the OS:

- **macOS**: `CFBundleDocumentTypes` in `Info.plist` handles double-click on `.ssproj`
- **Windows**: `fileAssociations` in electron-builder creates registry entries
- **Opening**: Electron's `open-file` event passes the path to `main.js`, which injects it via `preload.js` into the browser context, which calls `callApi("/api/project/open", {path})`

## What does NOT change

- The Python backend code (`server.py`, `controller.py`, `pipeline.py`, etc.) stays exactly as-is
- The browser static assets (`app.js`, `index.html`, modules) stay exactly as-is
- All 438 tests still pass
- `uv run splitshot` still works for development

## What changes

- New files (6 total) in `electron/` and `scripts/`
- `.gitignore` updated to exclude `electron/bundle/` and `electron/build/`
- No changes to any existing Python or JS source files

## Remaining risks

- **Bundle size**: ~150MB for the .dmg (Python + PySide6 + numpy + FFmpeg). This is normal for Electron + Python apps but worth noting.
- **PyQt licensing**: PySide6 is LGPL, which is compatible with commercial distribution. No legal issue.
- **macOS notarization**: The .dmg may need Apple notarization to avoid Gatekeeper warnings. This requires an Apple Developer account ($99/year).
- **Auto-update**: Not included in this plan. Can be added later with `electron-updater`.
- **Qt WebEngine**: PySide6+QtWebEngine is bundled, which adds ~50MB. Used for PractiScore session auth. If the PractiScore flow changes, this could be removed.

## Test plan

```bash
# 1. Build and run locally
npm --prefix electron run build:mac
open electron/build/SplitShot.dmg

# 2. Verify the app opens without terminal
# 3. Import a video, run analysis, verify shots detected
# 4. Export a video, verify output file
# 5. Double-click a .ssproj file, verify it opens in SplitShot
# 6. Verify all menu bar items work (File > Open, etc.)

# 7. Regression: existing dev workflow still works
uv run splitshot --check
uv run pytest tests/
```

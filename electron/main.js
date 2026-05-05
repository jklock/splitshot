const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require('electron');
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
  return path.join(__dirname, 'bundle');
}

function getPythonBinary() {
  const bundle = getBundlePath();
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(bundle, '.venv', binDir, `python${ext}`);
}

function getPythonArgs() {
  if (app.isPackaged) {
    return ['-m', 'splitshot', '--headless', '--no-open'];
  }
  const root = path.resolve(__dirname, '..');
  return ['run', '--directory', root, 'splitshot', '--headless', '--no-open'];
}

function startPythonBackend() {
  const args = getPythonArgs();
  const python = getPythonBinary();
  const bundlePath = getBundlePath();
  const env = { ...process.env };

  if (app.isPackaged) {
    env.PYTHONPATH = path.join(bundlePath, 'src');
    pythonProcess = spawn(python, args, {
      cwd: bundlePath,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } else {
    pythonProcess = spawn('uv', args, {
      cwd: path.resolve(__dirname, '..'),
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  }

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

function buildAppMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
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
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Project...',
          accelerator: 'CmdOrCtrl+O',
          click: async () => {
            const result = await dialog.showOpenDialog(mainWindow, {
              properties: ['openFile'],
              filters: [{ name: 'SplitShot Projects', extensions: ['ssproj'] }],
            });
            if (!result.canceled && result.filePaths[0] && mainWindow) {
              mainWindow.webContents.send('open-project', result.filePaths[0]);
            }
          },
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' },
      ],
    },
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
    {
      label: 'Help',
      submenu: [
        {
          label: 'SplitShot Website',
          click: () => shell.openExternal('https://splitshot.studio'),
        },
        {
          label: 'Report Issue',
          click: () => shell.openExternal('https://github.com/anomalyco/splitshot/issues'),
        },
      ],
    },
  ];
  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

ipcMain.handle('get-version', () => app.getVersion());

ipcMain.handle('get-platform', () => process.platform);

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

ipcMain.handle('open-project-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [{ name: 'SplitShot Projects', extensions: ['ssproj'] }],
  });
  return result.canceled ? null : result.filePaths[0];
});

app.on('ready', async () => {
  buildAppMenu();
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

app.on('open-file', (event, filePath) => {
  event.preventDefault();
  if (mainWindow) {
    mainWindow.webContents.send('open-project', filePath);
  }
});

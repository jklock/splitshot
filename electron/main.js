const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require('electron');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const {
  createLaunchIntentRouter,
  createProjectIntent,
  launchIntentFromArgv,
  launchIntentFromUrl,
} = require('./launch-intent');

let mainWindow = null;
let pythonProcess = null;
let backendStarted = false;
let initialLaunchIntent = launchIntentFromArgv(process.argv);
let windowLoaded = false;
let windowReadyToShow = false;
const PORT = Number.parseInt(process.env.SPLITSHOT_TEST_PORT || '8765', 10);
const PYTHON_URL = `http://127.0.0.1:${PORT}`;
const launchIntentRouter = createLaunchIntentRouter(dispatchLaunchIntent);
const TEST_READY_FILE = process.env.SPLITSHOT_ELECTRON_READY_FILE || '';
const TEST_EXIT_AFTER_READY = process.env.SPLITSHOT_ELECTRON_EXIT_AFTER_READY === '1';
let appReadyRecorded = false;

// On Windows, requestSingleInstanceLock() silently fails when elevated (admin/SYSTEM).
// GitHub Actions runners run elevated, causing app.quit() immediately.
// See https://github.com/electron/electron/issues/35681
// When SPLITSHOT_ELECTRON_TEST is set (CI), bypass the lock entirely.
if (!process.env.SPLITSHOT_ELECTRON_TEST && !app.requestSingleInstanceLock()) {
  app.quit();
}

function getBundlePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'bundle');
  }
  return path.join(__dirname, 'bundle');
}

function appendTestEvent(event, payload = {}) {
  if (!TEST_READY_FILE) return;
  const record = {
    event,
    pid: process.pid,
    ts: new Date().toISOString(),
    ...payload,
  };
  fs.mkdirSync(path.dirname(TEST_READY_FILE), { recursive: true });
  fs.appendFileSync(TEST_READY_FILE, `${JSON.stringify(record)}\n`, 'utf8');
}

function maybeRecordAppReady() {
  if (appReadyRecorded || !launchIntentRouter.isBackendReady() || !windowLoaded || !windowReadyToShow) {
    return;
  }
  appReadyRecorded = true;
  appendTestEvent('app-ready', {
    url: PYTHON_URL,
    initialProjectPath: initialLaunchIntent?.projectPath || null,
  });
  if (TEST_EXIT_AFTER_READY) {
    setTimeout(() => {
      app.quit();
    }, 1000);
  }
}

function getPythonBinary() {
  const bundle = getBundlePath();
  if (app.isPackaged && process.platform === 'win32') {
    return path.join(bundle, 'python', 'python.exe');
  }
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(bundle, '.venv', binDir, `python${ext}`);
}

function getPythonArgs(initialProjectPath = null) {
  const portArgs = ['--port', String(PORT)];
  const projectArgs = initialProjectPath ? ['--project', initialProjectPath] : [];
  if (app.isPackaged) {
    return ['-m', 'splitshot', '--headless', '--no-open', ...portArgs, ...projectArgs];
  }
  const root = path.resolve(__dirname, '..');
  return ['run', '--directory', root, 'splitshot', '--headless', '--no-open', ...portArgs, ...projectArgs];
}

function startPythonBackend(initialProjectPath = null) {
  const args = getPythonArgs(initialProjectPath);
  const python = getPythonBinary();
  const bundlePath = getBundlePath();
  const env = { ...process.env };
  backendStarted = true;

  if (app.isPackaged) {
    env.PYTHONPATH = path.join(bundlePath, 'src');
    env.PYTHONNOUSERSITE = '1';
    if (process.platform === 'win32') {
      const pythonHome = path.join(bundlePath, 'python');
      env.PYTHONHOME = pythonHome;
      env.PATH = `${pythonHome};${path.join(pythonHome, 'Scripts')};${env.PATH || ''}`;
    }
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
    appendTestEvent('backend-exit', { code });
    console.log(`Python backend exited with code ${code}`);
    if (!app.isQuitting) {
      app.quit();
    }
  });

  pythonProcess.on('error', (error) => {
    appendTestEvent('backend-spawn-error', { error: String(error) });
    console.error(`Python backend spawn failed: ${error}`);
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

  mainWindow.webContents.once('did-finish-load', () => {
    windowLoaded = true;
    launchIntentRouter.setWindowReady(true);
    appendTestEvent('window-loaded', { url: PYTHON_URL });
    maybeRecordAppReady();
  });

  mainWindow.once('ready-to-show', () => {
    windowReadyToShow = true;
    mainWindow.show();
    appendTestEvent('window-ready-to-show');
    maybeRecordAppReady();
  });

  mainWindow.on('closed', () => {
    windowLoaded = false;
    windowReadyToShow = false;
    launchIntentRouter.setWindowReady(false);
    appendTestEvent('window-closed');
    mainWindow = null;
  });
}

function dispatchLaunchIntent(intent) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return false;
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
  appendTestEvent('launch-intent-dispatched', {
    source: intent.source,
    projectPath: intent.projectPath,
  });
  mainWindow.webContents.send('open-project', intent.projectPath);
  return true;
}

function ensureWindowForQueuedLaunchIntent() {
  if (app.isReady() && !mainWindow && launchIntentRouter.isBackendReady()) {
    createWindow();
  }
}

function queueLaunchIntent(intent, { allowStartupProject = false } = {}) {
  if (!intent) return false;
  if (!backendStarted && allowStartupProject && !initialLaunchIntent) {
    initialLaunchIntent = intent;
    return true;
  }
  const queued = launchIntentRouter.queueIntent(intent);
  if (queued) ensureWindowForQueuedLaunchIntent();
  return queued;
}

function handleFileOpenPath(filePath, options = {}) {
  return queueLaunchIntent(createProjectIntent(filePath, options.source || 'file'), options);
}

function handleProtocolUrl(targetUrl, options = {}) {
  return queueLaunchIntent(launchIntentFromUrl(targetUrl), options);
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
              handleFileOpenPath(result.filePaths[0], { source: 'dialog' });
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

if (process.platform === 'darwin') {
  app.on('open-file', (event, filePath) => {
    event.preventDefault();
    handleFileOpenPath(filePath, { source: 'open-file', allowStartupProject: true });
  });

  app.on('open-url', (event, targetUrl) => {
    event.preventDefault();
    handleProtocolUrl(targetUrl, { allowStartupProject: true });
  });
}

app.on('second-instance', (_event, commandLine) => {
  const argvIntent = launchIntentFromArgv(commandLine);
  if (argvIntent) {
    queueLaunchIntent(argvIntent);
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.show();
    mainWindow.focus();
  }
});

if (process.env.SPLITSHOT_ELECTRON_TEST === '1') {
  ipcMain.handle('test-open-project', async (_event, targetPath) => handleFileOpenPath(targetPath, { source: 'test' }));
  ipcMain.handle('test-open-url', async (_event, targetUrl) => handleProtocolUrl(targetUrl));
  ipcMain.handle('test-simulate-second-instance', async (_event, argv) => {
    const argvIntent = launchIntentFromArgv(Array.isArray(argv) ? argv : [argv]);
    if (!argvIntent) return false;
    queueLaunchIntent(argvIntent);
    return true;
  });
}

app.on('ready', async () => {
  appendTestEvent('app-ready-start', {
    argv: process.argv,
    port: PORT,
  });
  buildAppMenu();
  startPythonBackend(initialLaunchIntent ? initialLaunchIntent.projectPath : null);
  try {
    await waitForServer();
    console.log('Python backend is ready');
    launchIntentRouter.setBackendReady(true);
    appendTestEvent('backend-ready', { url: PYTHON_URL });
    maybeRecordAppReady();
    createWindow();
  } catch (err) {
    appendTestEvent('startup-error', { error: String(err) });
    console.error(err);
    dialog.showErrorBox('Startup Error', 'Failed to start the SplitShot backend. Please try reinstalling the application.');
    app.quit();
  }
});

app.on('window-all-closed', () => {
  launchIntentRouter.setWindowReady(false);
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
  appendTestEvent('before-quit');
  launchIntentRouter.setWindowReady(false);
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
});

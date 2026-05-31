const { app, BrowserWindow, dialog, ipcMain, Menu, session, shell } = require('electron');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const { createDesktopRouteBridgeSource } = require('./desktop-route-bridge-source');
const { createPractiScoreHost } = require('./practiscore-host');
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
const REQUESTED_PORT = Number.parseInt(process.env.SPLITSHOT_TEST_PORT || '0', 10);
const BACKEND_READY_PREFIX = 'SPLITSHOT_READY ';
const BACKEND_START_TIMEOUT_MS = Number.parseInt(process.env.SPLITSHOT_ELECTRON_BACKEND_TIMEOUT_MS || '30000', 10) || 30000;
const PRACTISCORE_DASHBOARD_URL = 'https://practiscore.com/dashboard/home';
const VIDEO_EXTENSIONS = ['mp4', 'm4v', 'mov', 'avi', 'webm', 'mkv', 'wmv', 'mpg', 'mpeg', 'mts', 'm2ts'];
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tif', 'tiff'];
const EXPORT_EXTENSIONS = ['mp4', 'm4v', 'mov', 'mkv'];
const PROJECT_DIALOG_KINDS = new Set(['project', 'project_save', 'project_open', 'project_folder']);
const launchIntentRouter = createLaunchIntentRouter(dispatchLaunchIntent);
const TEST_READY_FILE = process.env.SPLITSHOT_ELECTRON_READY_FILE || '';
const TEST_EXIT_AFTER_READY = process.env.SPLITSHOT_ELECTRON_EXIT_AFTER_READY === '1';
const TEST_DIALOG_PATH = process.env.SPLITSHOT_ELECTRON_TEST_DIALOG_PATH || '';
const TEST_CAPTURE_EXTERNAL_OPEN = process.env.SPLITSHOT_ELECTRON_TEST_OPEN_EXTERNAL_CAPTURE === '1';
const PRACTISCORE_HOST_ENABLED = process.env.SPLITSHOT_ELECTRON_PRACTISCORE_HOST_V1 === '1';
let appReadyRecorded = false;
let lastExternalOpenUrl = null;
let backendReadyPayload = null;
let backendSessionMetadata = null;
let backendBaseUrl = null;
let practiScoreHost = null;

function getPractiScoreHost() {
  if (!practiScoreHost) {
    practiScoreHost = createPractiScoreHost({
      enabled: PRACTISCORE_HOST_ENABLED,
      BrowserWindow,
      session,
      getParentWindow: () => mainWindow,
    });
  }
  return practiScoreHost;
}

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

function getElectronSupportRoots() {
  try {
    return {
      electronLogRoot: app.getPath('logs'),
      electronUserDataRoot: app.getPath('userData'),
      electronCrashDumpsRoot: app.getPath('crashDumps'),
    };
  } catch {
    return {
      electronLogRoot: null,
      electronUserDataRoot: null,
      electronCrashDumpsRoot: null,
    };
  }
}

function maybeRecordAppReady() {
  if (appReadyRecorded || !launchIntentRouter.isBackendReady() || !windowLoaded || !windowReadyToShow) {
    return;
  }
  appReadyRecorded = true;
  appendTestEvent('app-ready', {
    url: backendBaseUrl,
    initialProjectPath: initialLaunchIntent?.projectPath || null,
  });
  if (TEST_EXIT_AFTER_READY) {
    setTimeout(() => {
      app.quit();
    }, 1000);
  }
}

function parseBackendReadyLine(line) {
  if (typeof line !== 'string' || !line.startsWith(BACKEND_READY_PREFIX)) {
    return null;
  }
  const rawPayload = line.slice(BACKEND_READY_PREFIX.length).trim();
  let payload;
  try {
    payload = JSON.parse(rawPayload);
  } catch (error) {
    throw new Error(`Invalid SplitShot ready line payload: ${error?.message || error}`);
  }
  if (!payload || typeof payload !== 'object') {
    throw new Error('Invalid SplitShot ready line payload.');
  }
  if (typeof payload.base_url !== 'string' || !payload.base_url.trim()) {
    throw new Error('SplitShot ready line did not include a base_url.');
  }
  if (typeof payload.claim_path !== 'string' || !payload.claim_path.trim()) {
    throw new Error('SplitShot ready line did not include a claim_path.');
  }
  if (typeof payload.bootstrap_token !== 'string' || !payload.bootstrap_token.trim()) {
    throw new Error('SplitShot ready line did not include a bootstrap_token.');
  }
  return payload;
}

function parseSetCookieHeader(setCookieHeader) {
  if (typeof setCookieHeader !== 'string' || !setCookieHeader.trim()) {
    throw new Error('SplitShot backend did not return a session cookie.');
  }
  const [cookiePair] = setCookieHeader.split(';');
  const separatorIndex = cookiePair.indexOf('=');
  if (separatorIndex <= 0) {
    throw new Error('SplitShot backend returned an invalid session cookie.');
  }
  return {
    name: cookiePair.slice(0, separatorIndex).trim(),
    value: cookiePair.slice(separatorIndex + 1).trim(),
  };
}

async function applyBackendSessionCookie(setCookieHeader, baseUrl) {
  const cookie = parseSetCookieHeader(setCookieHeader);
  await session.defaultSession.cookies.set({
    url: baseUrl,
    name: cookie.name,
    value: cookie.value,
    path: '/',
    httpOnly: true,
    sameSite: 'strict',
  });
}

async function establishBackendSession(readyPayload) {
  const claimUrl = new URL(readyPayload.claim_path, readyPayload.base_url).toString();
  const response = await fetch(claimUrl, {
    method: 'POST',
    headers: {
      'X-SplitShot-Bootstrap-Token': readyPayload.bootstrap_token,
    },
  });
  if (!response.ok) {
    const responseText = await response.text();
    throw new Error(`SplitShot backend claim failed (${response.status}): ${responseText}`);
  }
  const setCookieHeader = response.headers.getSetCookie?.()[0] || response.headers.get('set-cookie');
  await applyBackendSessionCookie(setCookieHeader, readyPayload.base_url);
  const claimPayload = await response.json();
  backendReadyPayload = readyPayload;
  backendBaseUrl = readyPayload.base_url;
  backendSessionMetadata = {
    ...claimPayload,
    base_url: readyPayload.base_url,
    startup_status_path: readyPayload.startup_status_path,
    claim_path: readyPayload.claim_path,
  };
  return backendSessionMetadata;
}

function processPythonStdoutChunk(chunk, onReadyLine) {
  const text = String(chunk || '');
  const lines = text.split(/\r?\n/);
  return lines.reduce((remainder, line, index) => {
    const isLast = index === lines.length - 1;
    if (isLast && !text.endsWith('\n') && !text.endsWith('\r')) {
      return line;
    }
    if (line) {
      console.log(`[python] ${line}`);
      const payload = parseBackendReadyLine(line);
      if (payload) {
        onReadyLine(payload);
      }
    }
    return '';
  }, '');
}

function expandUserPath(value) {
  if (typeof value !== 'string') return '';
  if (value === '~') return os.homedir();
  if (value.startsWith(`~${path.sep}`)) {
    return path.join(os.homedir(), value.slice(2));
  }
  if (path.sep === '\\' && value.startsWith('~/')) {
    return path.join(os.homedir(), value.slice(2).replace(/\//g, '\\'));
  }
  return value;
}

function resolveProjectDialogTarget(candidatePath) {
  if (typeof candidatePath !== 'string' || !candidatePath.trim()) return '';
  const expanded = expandUserPath(candidatePath.trim());
  const resolved = path.resolve(expanded);
  return path.basename(resolved).toLowerCase() === 'project.json'
    ? path.dirname(resolved)
    : resolved;
}

function resolveExistingDialogDirectory(candidatePath, { projectPath = false } = {}) {
  if (typeof candidatePath !== 'string' || !candidatePath.trim()) return null;
  const resolvedTarget = projectPath
    ? resolveProjectDialogTarget(candidatePath)
    : path.resolve(expandUserPath(candidatePath.trim()));
  if (!resolvedTarget) return null;
  try {
    const stats = fs.statSync(resolvedTarget);
    return stats.isDirectory() ? resolvedTarget : path.dirname(resolvedTarget);
  } catch {}

  let probe = path.dirname(resolvedTarget);
  while (probe) {
    try {
      if (fs.statSync(probe).isDirectory()) {
        return probe;
      }
    } catch {}
    const nextProbe = path.dirname(probe);
    if (nextProbe === probe) break;
    probe = nextProbe;
  }
  return null;
}

function dialogDefaultPath(kind, current, home) {
  const projectPath = PROJECT_DIALOG_KINDS.has(String(kind || '').trim());
  return (
    resolveExistingDialogDirectory(current, { projectPath })
    || resolveExistingDialogDirectory(home, { projectPath })
    || app.getPath('home')
  );
}

async function showPathDialog(request = {}) {
  const kind = String(request?.kind || '').trim();
  const current = String(request?.current || '').trim();
  const home = String(request?.home || '').trim();
  if (process.env.SPLITSHOT_ELECTRON_TEST === '1' && TEST_DIALOG_PATH) {
    return TEST_DIALOG_PATH;
  }

  const browserWindow = mainWindow && !mainWindow.isDestroyed() ? mainWindow : undefined;
  const defaultPath = dialogDefaultPath(kind, current, home);
  if (kind === 'primary' || kind === 'secondary') {
    const result = await dialog.showOpenDialog(browserWindow, {
      defaultPath,
      properties: ['openFile'],
      filters: [
        { name: 'Image files', extensions: IMAGE_EXTENSIONS },
        { name: 'Video files', extensions: VIDEO_EXTENSIONS },
        { name: 'All files', extensions: ['*'] },
      ],
    });
    return result.canceled ? null : result.filePaths[0] || null;
  }
  if (kind === 'popup_image') {
    const result = await dialog.showOpenDialog(browserWindow, {
      defaultPath,
      properties: ['openFile'],
      filters: [
        { name: 'Image files', extensions: IMAGE_EXTENSIONS },
        { name: 'All files', extensions: ['*'] },
      ],
    });
    return result.canceled ? null : result.filePaths[0] || null;
  }
  if (PROJECT_DIALOG_KINDS.has(kind)) {
    const properties = ['openDirectory'];
    if (process.platform === 'darwin') properties.push('treatPackageAsDirectory');
    const result = await dialog.showOpenDialog(browserWindow, {
      defaultPath,
      properties,
    });
    return result.canceled ? null : result.filePaths[0] || null;
  }
  if (kind === 'export') {
    const defaultName = current ? path.basename(current) : 'output.mp4';
    const result = await dialog.showSaveDialog(browserWindow, {
      defaultPath: path.join(defaultPath, defaultName),
      filters: [
        { name: 'Video files', extensions: EXPORT_EXTENSIONS },
        { name: 'All files', extensions: ['*'] },
      ],
    });
    return result.canceled ? null : result.filePath || null;
  }
  throw new Error(`Unsupported path chooser kind: ${kind}`);
}

async function openExternalUrl(targetUrl) {
  if (typeof targetUrl !== 'string' || !targetUrl.trim()) {
    return false;
  }
  let parsedUrl;
  try {
    parsedUrl = new URL(targetUrl);
  } catch {
    return false;
  }
  if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
    return false;
  }
  const normalizedUrl = parsedUrl.toString();
  lastExternalOpenUrl = normalizedUrl;
  if (process.env.SPLITSHOT_ELECTRON_TEST === '1' && TEST_CAPTURE_EXTERNAL_OPEN) {
    return true;
  }
  try {
    await shell.openExternal(normalizedUrl);
    return true;
  } catch {
    return false;
  }
}

function createDesktopRouteBridgeScript() {
  return createDesktopRouteBridgeSource({ dashboardUrl: PRACTISCORE_DASHBOARD_URL });
}

async function installDesktopRouteBridge(browserWindow, attemptsRemaining = 20) {
  if (!browserWindow || browserWindow.isDestroyed()) {
    return false;
  }
  try {
    await browserWindow.webContents.executeJavaScript(createDesktopRouteBridgeScript(), true);
    const bridgeDiagnostics = await browserWindow.webContents.executeJavaScript(`(() => ({
      splitshot: Boolean(window.splitshot),
      installed: window.__splitshotDesktopRouteBridgeInstalled === true,
      installing: window.__splitshotDesktopRouteBridgeInstalling === true,
    }))()`, true);
    if (bridgeDiagnostics.installed) {
      return true;
    }
    if (attemptsRemaining > 0) {
      setTimeout(() => {
        void installDesktopRouteBridge(browserWindow, attemptsRemaining - 1);
      }, 100);
    }
    return false;
  } catch (error) {
    appendTestEvent('desktop-route-bridge-error', { error: String(error) });
    console.error(`Failed to install desktop route bridge: ${error}`);
    if (attemptsRemaining > 0) {
      setTimeout(() => {
        void installDesktopRouteBridge(browserWindow, attemptsRemaining - 1);
      }, 100);
    }
    return false;
  }
}

function getPythonBinary() {
  if (!app.isPackaged && process.env.SPLITSHOT_PYTHON_EXECUTABLE) {
    return process.env.SPLITSHOT_PYTHON_EXECUTABLE;
  }
  const bundle = getBundlePath();
  if (app.isPackaged && process.platform === 'win32') {
    return path.join(bundle, 'python', 'python.exe');
  }
  if (!app.isPackaged) {
    const root = path.resolve(__dirname, '..');
    const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
    const ext = process.platform === 'win32' ? '.exe' : '';
    return path.join(root, '.venv', binDir, `python${ext}`);
  }
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(bundle, '.venv', binDir, `python${ext}`);
}

function getPythonArgs(initialProjectPath = null) {
  const portArgs = ['--port', String(Number.isFinite(REQUESTED_PORT) ? REQUESTED_PORT : 0)];
  const projectArgs = initialProjectPath ? ['--project', initialProjectPath] : [];
  return ['-m', 'splitshot', '--headless', '--no-open', ...portArgs, ...projectArgs];
}

function prependPathEntries(env, entries) {
  const separator = process.platform === 'win32' ? ';' : ':';
  const existing = (env.PATH || '').split(separator).filter(Boolean);
  const next = [...entries.filter(Boolean), ...existing];
  env.PATH = next.join(separator);
}

function getBundledFfmpegDir(bundlePath) {
  const platform = process.platform === 'darwin' ? 'macos' : process.platform === 'win32' ? 'windows' : 'linux';
  return path.join(bundlePath, 'src', 'splitshot', 'resources', 'ffmpeg', platform);
}

function getBundledSitePackagesDir(bundlePath) {
  if (process.platform === 'win32') {
    return path.join(bundlePath, 'python', 'Lib', 'site-packages');
  }
  const libRoot = path.join(bundlePath, '.venv', 'lib');
  const entry = fs.readdirSync(libRoot, { withFileTypes: true })
    .find((item) => item.isDirectory() && item.name.startsWith('python'));
  if (!entry) {
    throw new Error(`Bundled site-packages root not found under ${libRoot}`);
  }
  return path.join(libRoot, entry.name, 'site-packages');
}

function startPythonBackend(initialProjectPath = null) {
  return new Promise((resolve, reject) => {
  const args = getPythonArgs(initialProjectPath);
  const python = getPythonBinary();
  const bundlePath = getBundlePath();
  const projectRoot = path.resolve(__dirname, '..');
  const env = { ...process.env };
  let settled = false;
  let stdoutBuffer = '';
  let readyTimer = null;
  backendStarted = true;
  env.SPLITSHOT_REQUIRE_SESSION_CLAIM = '1';

  const settleOnce = (callback) => (value) => {
    if (settled) return;
    settled = true;
    if (readyTimer) {
      clearTimeout(readyTimer);
      readyTimer = null;
    }
    callback(value);
  };
  const resolveOnce = settleOnce(resolve);
  const rejectOnce = settleOnce(reject);

  if (app.isPackaged) {
    env.PYTHONPATH = path.join(bundlePath, 'src');
    env.PYTHONNOUSERSITE = '1';
    prependPathEntries(env, [getBundledFfmpegDir(bundlePath)]);
    if (process.platform === 'win32') {
      const pythonHome = path.join(bundlePath, 'python');
      env.PYTHONHOME = pythonHome;
      env.PYTHONPATH += ';' + getBundledSitePackagesDir(bundlePath);
      prependPathEntries(env, [pythonHome, path.join(pythonHome, 'Scripts')]);
    } else {
      const venvHome = path.join(bundlePath, '.venv');
      env.PYTHONHOME = venvHome;
      env.PYTHONPATH += ':' + getBundledSitePackagesDir(bundlePath);
    }
    pythonProcess = spawn(python, args, {
      cwd: bundlePath,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } else {
    pythonProcess = spawn(python, args, {
      cwd: projectRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  }

  readyTimer = setTimeout(() => {
    rejectOnce(new Error('Python backend failed to emit a ready line.'));
  }, BACKEND_START_TIMEOUT_MS);

  pythonProcess.stdout.on('data', (data) => {
    try {
      stdoutBuffer = processPythonStdoutChunk(stdoutBuffer + data.toString(), (payload) => {
        void establishBackendSession(payload)
          .then(resolveOnce)
          .catch(rejectOnce);
      });
    } catch (error) {
      rejectOnce(error);
    }
  });

  pythonProcess.stderr.on('data', (data) => {
    for (const line of String(data || '').split(/\r?\n/)) {
      if (line) {
        console.error(`[python] ${line}`);
      }
    }
  });

  pythonProcess.on('exit', (code) => {
    appendTestEvent('backend-exit', { code });
    console.log(`Python backend exited with code ${code}`);
    if (!settled) {
      rejectOnce(new Error(`Python backend exited with code ${code}`));
    }
    if (!app.isQuitting) {
      app.quit();
    }
  });

  pythonProcess.on('error', (error) => {
    appendTestEvent('backend-spawn-error', { error: String(error) });
    console.error(`Python backend spawn failed: ${error}`);
    rejectOnce(error);
  });
  });
}

function createWindow() {
  if (!backendBaseUrl) {
    throw new Error('SplitShot backend URL is unavailable.');
  }
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
      sandbox: false,
    },
    show: false,
  });

  mainWindow.webContents.on('dom-ready', () => {
    void installDesktopRouteBridge(mainWindow);
  });

  mainWindow.webContents.once('did-finish-load', () => {
    void installDesktopRouteBridge(mainWindow);
    windowLoaded = true;
    launchIntentRouter.setWindowReady(true);
    appendTestEvent('window-loaded', { url: backendBaseUrl });
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

  mainWindow.loadURL(backendBaseUrl);
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
            const selectedPath = await showPathDialog({ kind: 'project_folder' });
            if (selectedPath && mainWindow) {
              handleFileOpenPath(selectedPath, { source: 'dialog' });
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
          click: () => openExternalUrl('https://splitshot.studio'),
        },
        {
          label: 'Report Issue',
          click: () => openExternalUrl('https://github.com/anomalyco/splitshot/issues'),
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
  return showPathDialog({ kind: 'project_folder' });
});

ipcMain.handle('open-path-dialog', async (_event, request) => showPathDialog(request));

ipcMain.handle('open-external', async (_event, targetUrl) => openExternalUrl(targetUrl));

ipcMain.handle('install-desktop-route-bridge', async () => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return false;
  }
  return installDesktopRouteBridge(mainWindow);
});

ipcMain.handle('get-practiscore-host-feature', async () => getPractiScoreHost().getFeatureState());

ipcMain.handle('get-practiscore-state-overlay', async () => getPractiScoreHost().getStateOverlay());

ipcMain.handle('start-practiscore-session-host', async () => getPractiScoreHost().startSession());

ipcMain.handle('get-practiscore-session-status-host', async () => getPractiScoreHost().currentStatus());

ipcMain.handle('clear-practiscore-session-host', async () => getPractiScoreHost().clearSession());

ipcMain.handle('list-practiscore-matches-host', async () => getPractiScoreHost().listMatches());

ipcMain.handle('download-practiscore-selected-match-host', async (_event, remoteId) => getPractiScoreHost().downloadSelectedMatch(remoteId));

ipcMain.handle('update-practiscore-host-overlay', async (_event, routePayload) => getPractiScoreHost().updateOverlay(routePayload));

ipcMain.handle('claim-backend-session', async () => {
  if (!backendSessionMetadata) {
    throw new Error('SplitShot backend session is not ready.');
  }
  return backendSessionMetadata;
});

ipcMain.handle('get-backend-session-metadata', async () => backendSessionMetadata);

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
  ipcMain.handle('test-get-last-open-external', async () => lastExternalOpenUrl);
}

app.on('ready', async () => {
  app.setAppLogsPath();
  appendTestEvent('app-ready-start', {
    argv: process.argv,
    requestedPort: REQUESTED_PORT,
    ...getElectronSupportRoots(),
  });
  buildAppMenu();
  try {
    const metadata = await startPythonBackend(initialLaunchIntent ? initialLaunchIntent.projectPath : null);
    console.log('Python backend is ready');
    launchIntentRouter.setBackendReady(true);
    appendTestEvent('backend-ready', {
      url: backendBaseUrl,
      sessionId: metadata?.session_id || null,
      healthPath: metadata?.health_path || null,
      eventsPath: metadata?.events_path || null,
      logRoot: metadata?.log_root || null,
      cacheRoot: metadata?.cache_root || null,
      appDataRoot: metadata?.app_data_root || null,
      ...getElectronSupportRoots(),
    });
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

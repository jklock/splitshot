const { contextBridge, ipcRenderer } = require('electron');

let _pendingProjectPath = null;

ipcRenderer.on('open-project', (_event, path) => {
  if (typeof _pendingProjectPath === 'function') {
    _pendingProjectPath(path);
  } else {
    _pendingProjectPath = path;
  }
});

const splitshotBridge = {
  getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  openFile: () => ipcRenderer.invoke('open-file'),
  openProjectDialog: () => ipcRenderer.invoke('open-project-dialog'),
  onOpenProject: (callback) => {
    if (_pendingProjectPath !== null && typeof _pendingProjectPath !== 'function') {
      callback(_pendingProjectPath);
    }
    _pendingProjectPath = callback;
  },
};

if (process.env.SPLITSHOT_ELECTRON_TEST === '1') {
  splitshotBridge.testOpenProject = (targetPath) => ipcRenderer.invoke('test-open-project', targetPath);
  splitshotBridge.testOpenUrl = (targetUrl) => ipcRenderer.invoke('test-open-url', targetUrl);
  splitshotBridge.testSimulateSecondInstance = (argv) => ipcRenderer.invoke('test-simulate-second-instance', argv);
}

contextBridge.exposeInMainWorld('splitshot', splitshotBridge);

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
  openPathDialog: (request) => ipcRenderer.invoke('open-path-dialog', request),
  openExternal: (targetUrl) => ipcRenderer.invoke('open-external', targetUrl),
  getPractiScoreHostFeature: () => ipcRenderer.invoke('get-practiscore-host-feature'),
  getPractiScoreStateOverlay: () => ipcRenderer.invoke('get-practiscore-state-overlay'),
  startPractiScoreSessionHost: () => ipcRenderer.invoke('start-practiscore-session-host'),
  getPractiScoreSessionStatusHost: () => ipcRenderer.invoke('get-practiscore-session-status-host'),
  clearPractiScoreSessionHost: () => ipcRenderer.invoke('clear-practiscore-session-host'),
  listPractiScoreMatchesHost: () => ipcRenderer.invoke('list-practiscore-matches-host'),
  downloadPractiScoreSelectedMatchHost: (remoteId) => ipcRenderer.invoke('download-practiscore-selected-match-host', remoteId),
  updatePractiScoreHostOverlay: (routePayload) => ipcRenderer.invoke('update-practiscore-host-overlay', routePayload),
  claimBackendSession: () => ipcRenderer.invoke('claim-backend-session'),
  getBackendSessionMetadata: () => ipcRenderer.invoke('get-backend-session-metadata'),
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
  splitshotBridge.testGetLastOpenExternal = () => ipcRenderer.invoke('test-get-last-open-external');
}

contextBridge.exposeInMainWorld('splitshot', splitshotBridge);

window.addEventListener('DOMContentLoaded', () => {
  void ipcRenderer.invoke('install-desktop-route-bridge');
});

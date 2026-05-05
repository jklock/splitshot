const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splitshot', {
  getVersion: () => ipcRenderer.invoke('get-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  openFile: () => ipcRenderer.invoke('open-file'),
  openProjectDialog: () => ipcRenderer.invoke('open-project-dialog'),
  onOpenProject: (callback) => {
    ipcRenderer.on('open-project', (_event, path) => callback(path));
  },
});

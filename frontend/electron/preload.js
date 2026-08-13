const { contextBridge, ipcRenderer } = require('electron')

// Expose safe IPC API to renderer process (React)
contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
})

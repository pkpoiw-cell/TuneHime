const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 窗口控制
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  // WebSocket
  getWsPort: () => ipcRenderer.invoke('get-ws-port'),

  // 激活相关
  getActivationStatus: () => ipcRenderer.invoke('get-activation-status'),
  activate: (code) => ipcRenderer.invoke('activate', code),
  resetTrial: () => ipcRenderer.invoke('reset-trial'),  // 测试用
});

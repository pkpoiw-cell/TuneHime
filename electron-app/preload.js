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

  // 外部链接和目录
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  openLogDir: () => ipcRenderer.invoke('open-log-dir'),
  checkUpdate: () => ipcRenderer.invoke('check-update'),

  // 偏好设置
  getPreferences: () => ipcRenderer.invoke('get-preferences'),
  savePreference: (key, value) => ipcRenderer.invoke('save-preference', key, value),
  resetAllSettings: () => ipcRenderer.invoke('reset-all-settings'),

  // 开机自启
  getAutoLaunch: () => ipcRenderer.invoke('get-auto-launch'),
  setAutoLaunch: (enabled) => ipcRenderer.invoke('set-auto-launch', enabled),

  // 最小化到托盘
  getMinimizeToTray: () => ipcRenderer.invoke('get-minimize-to-tray'),
  setMinimizeToTray: (enabled) => ipcRenderer.invoke('set-minimize-to-tray', enabled),
});

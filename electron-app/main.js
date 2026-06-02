const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const Store = require('electron-store');
const { validateActivationCode } = require('./activation');

// 初始化本地存储
const store = new Store();

let mainWindow = null;
const WS_PORT = 9876;

// 试用期配置
const TRIAL_DAYS = 3;
const TRIAL_MS = TRIAL_DAYS * 24 * 60 * 60 * 1000;

/**
 * 获取激活状态
 */
function getActivationStatus() {
  // 检查是否已激活
  const isActivated = store.get('activated', false);
  if (isActivated) {
    return { status: 'activated', activatedAt: store.get('activatedAt') };
  }

  // 检查试用期
  let firstLaunch = store.get('firstLaunch');
  if (!firstLaunch) {
    firstLaunch = Date.now();
    store.set('firstLaunch', firstLaunch);
  }

  const elapsed = Date.now() - firstLaunch;
  const remaining = TRIAL_MS - elapsed;
  const expired = remaining <= 0;

  return {
    status: expired ? 'expired' : 'trial',
    firstLaunch,
    remaining: Math.max(0, remaining),
    remainingDays: Math.max(0, Math.ceil(remaining / (24 * 60 * 60 * 1000))),
    expired
  };
}

/**
 * 验证并激活
 */
function activate(code) {
  const result = validateActivationCode(code);

  if (result.valid) {
    store.set('activated', true);
    store.set('activatedAt', Date.now());
    store.set('activationCode', code);
    store.set('licenseType', result.type);
    return { success: true, type: result.type };
  }

  return { success: false, error: '激活码无效' };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1160,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    frame: false,
    transparent: true,
    title: '音姬 TuneHime',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => { app.quit(); });
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// 窗口控制
ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window-close', () => mainWindow?.close());

// WebSocket 端口
ipcMain.handle('get-ws-port', () => WS_PORT);

// 激活相关 IPC
ipcMain.handle('get-activation-status', () => getActivationStatus());
ipcMain.handle('activate', (event, code) => activate(code));
ipcMain.handle('reset-trial', () => {
  // 重置试用期（仅用于测试，生产环境可删除）
  store.delete('firstLaunch');
  store.delete('activated');
  store.delete('activatedAt');
  store.delete('activationCode');
  store.delete('licenseType');
  return { success: true };
});

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const Store = require('electron-store');
const { validateActivationCode } = require('./activation');

// 初始化本地存储
const store = new Store();

let mainWindow = null;
let serverProcess = null;
const WS_PORT = 9876;

// 试用期配置
const TRIAL_DAYS = 3;
const TRIAL_MS = TRIAL_DAYS * 24 * 60 * 60 * 1000;

/**
 * 获取服务器路径
 */
function getServerPath() {
  // 开发模式
  if (process.argv.includes('--dev')) {
    return path.join(__dirname, '..', 'python-backend', 'server.py');
  }

  // 打包后的路径
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'server', 'server.exe');
  }

  // 开发环境
  return path.join(__dirname, '..', 'python-backend', 'server.py');
}

/**
 * 启动 Python 后端服务器
 */
function startServer() {
  const serverPath = getServerPath();

  console.log('启动服务器:', serverPath);

  // 判断是 .exe 还是 .py
  if (serverPath.endsWith('.exe')) {
    serverProcess = spawn(serverPath, [], {
      cwd: path.dirname(serverPath),
      stdio: 'pipe'
    });
  } else {
    // 开发模式使用 py 命令
    serverProcess = spawn('py', [serverPath], {
      cwd: path.dirname(serverPath),
      stdio: 'pipe'
    });
  }

  serverProcess.stdout.on('data', (data) => {
    console.log('Server stdout:', data.toString());
  });

  serverProcess.stderr.on('data', (data) => {
    console.log('Server stderr:', data.toString());
  });

  serverProcess.on('error', (err) => {
    console.error('服务器启动失败:', err);
  });

  serverProcess.on('close', (code) => {
    console.log('服务器已关闭，退出码:', code);
    serverProcess = null;
  });
}

/**
 * 停止服务器
 */
function stopServer() {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

/**
 * 获取激活状态
 */
function getActivationStatus() {
  const isActivated = store.get('activated', false);
  if (isActivated) {
    return { status: 'activated', activatedAt: store.get('activatedAt') };
  }

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

// 应用启动
app.whenReady().then(() => {
  startServer();
  // 等待服务器启动后再打开窗口
  setTimeout(createWindow, 1500);
});

// 应用退出
app.on('window-all-closed', () => {
  stopServer();
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => {
  stopServer();
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
  store.delete('firstLaunch');
  store.delete('activated');
  store.delete('activatedAt');
  store.delete('activationCode');
  store.delete('licenseType');
  return { success: true };
});

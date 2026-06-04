const { app, BrowserWindow, ipcMain, dialog, shell, Tray, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn } = require('child_process');
const Store = require('electron-store');
const { validateActivationCode } = require('./activation');

// 初始化本地存储
const store = new Store();

let mainWindow = null;
let tray = null;
let serverProcess = null;
const WS_PORT = 9876;

/**
 * 检查端口是否可用
 */
function checkPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(port, '127.0.0.1', () => {
      server.close(() => resolve(true));
    });
    server.on('error', () => resolve(false));
  });
}

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

function getPythonPath() {
  // 常见 Python 安装路径
  const candidates = [
    // 用户本地安装
    path.join(app.getPath('home'), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
    path.join(app.getPath('home'), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
    path.join(app.getPath('home'), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
    path.join(app.getPath('home'), 'AppData', 'Local', 'Programs', 'Python', 'Python39', 'python.exe'),
    // 全局安装
    'C:\\Python312\\python.exe',
    'C:\\Python311\\python.exe',
    'C:\\Python310\\python.exe',
    'C:\\Python39\\python.exe',
    // 用户自定义路径
    path.join(app.getPath('home'), 'AppData', 'Local', 'Python', 'bin', 'python.exe'),
  ];

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }

  // 回退到 PATH 中的 python
  return 'python';
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
    serverProcess = spawn(getPythonPath(), [serverPath, String(WS_PORT)], {
      cwd: path.dirname(serverPath),
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'src')
      },
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
    if (mainWindow) {
      dialog.showErrorBox(
        '后端启动失败',
        `Python 后端启动失败，请检查 Python 是否已安装。\n\n错误信息: ${err.message}`
      );
    }
  });

  serverProcess.on('close', (code) => {
    console.log('服务器已关闭，退出码:', code);
    serverProcess = null;
    // 非正常退出时提示用户
    if (code !== 0 && code !== null && mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'warning',
        title: '后端已停止',
        message: `Python 后端异常退出 (退出码: ${code})，部分功能可能无法使用。`,
        buttons: ['确定']
      });
    }
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

function createTray() {
  const iconPath = path.join(__dirname, '..', 'resources', 'logo.png');
  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出音姬',
      click: () => {
        store.set('minimizeToTray', false); // 临时禁用托盘，确保退出
        app.quit();
      }
    }
  ]);

  tray.setToolTip('音姬 TuneHime');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
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

  // 窗口关闭时最小化到托盘
  mainWindow.on('close', (event) => {
    const minimizeToTray = store.get('minimizeToTray', true);
    if (minimizeToTray && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// 应用启动
app.whenReady().then(async () => {
  // 检查端口是否可用
  const portAvailable = await checkPortAvailable(WS_PORT);
  if (!portAvailable) {
    dialog.showErrorBox(
      '端口被占用',
      `端口 ${WS_PORT} 已被其他程序占用，请关闭占用该端口的程序后重试。`
    );
    app.quit();
    return;
  }

  startServer();

  // 创建系统托盘
  createTray();

  // 等待服务器启动后再打开窗口
  setTimeout(() => {
    createWindow();
    // 检查是否需要启动时最小化
    if (store.get('startMinimized', false)) {
      mainWindow.hide();
    }
  }, 1500);
});

// 应用退出
app.on('window-all-closed', () => {
  stopServer();
  if (tray) tray.destroy();
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => {
  app.isQuitting = true;
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

// 外部链接和目录
ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle('open-log-dir', () => {
  const logPath = path.join(app.getPath('userData'), 'logs');
  if (!fs.existsSync(logPath)) {
    fs.mkdirSync(logPath, { recursive: true });
  }
  shell.openPath(logPath);
});

ipcMain.handle('check-update', () => {
  // 简单的更新检查提示
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: '检查更新',
    message: '当前版本: V0.6.0',
    detail: '您正在使用最新版本。',
    buttons: ['确定']
  });
});

// 开机自启
ipcMain.handle('get-auto-launch', () => {
  return app.getLoginItemSettings().openAtLogin;
});

ipcMain.handle('set-auto-launch', (event, enabled) => {
  app.setLoginItemSettings({
    openAtLogin: enabled,
    path: app.getPath('exe')
  });
  return { success: true };
});

// 最小化到托盘设置
ipcMain.handle('get-minimize-to-tray', () => {
  return store.get('minimizeToTray', true);
});

ipcMain.handle('set-minimize-to-tray', (event, enabled) => {
  store.set('minimizeToTray', enabled);
  return { success: true };
});

// 获取所有偏好设置
ipcMain.handle('get-preferences', () => {
  return {
    autoLaunch: app.getLoginItemSettings().openAtLogin,
    minimizeToTray: store.get('minimizeToTray', true),
    startMinimized: store.get('startMinimized', false),
    checkUpdate: store.get('checkUpdate', true),
    sampleRate: store.get('sampleRate', 48000),
    bufferSize: store.get('bufferSize', 2048),
    lowLatency: store.get('lowLatency', false),
    theme: store.get('theme', 'light'),
    language: store.get('language', 'zh'),
    showFps: store.get('showFps', false),
    logLevel: store.get('logLevel', 'info'),
  };
});

// 保存偏好设置
ipcMain.handle('save-preference', (event, key, value) => {
  store.set(key, value);
  return { success: true };
});

// 重置所有设置
ipcMain.handle('reset-all-settings', () => {
  store.clear();
  return { success: true };
});

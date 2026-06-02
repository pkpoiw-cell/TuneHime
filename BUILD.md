# 音姬 TuneHime - 打包指南

## 环境要求

- **Python**: 3.8 或更高版本
- **Node.js**: 16 或更高版本
- **npm**: 通常随 Node.js 一起安装

## 一键打包（推荐）

```bash
build.bat
```

这将自动完成以下步骤：
1. 安装 Python 依赖
2. 安装 Node.js 依赖
3. 打包 Python 后端为 .exe
4. 下载 VB-CABLE 虚拟声卡
5. 打包 Electron 应用为安装程序

输出文件：`electron-app/dist/TuneHime-Setup-1.0.0.exe`

## 手动打包

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install pyinstaller

cd electron-app
npm install
```

### 2. 打包 Python 后端

```bash
python build_backend.py
```

输出：`python-backend/dist/server.exe`

### 3. 下载 VB-CABLE

```bash
download_vbcable.bat
```

或手动下载：
- 访问 https://vb-audio.com/Cable/
- 下载 VB-CABLE Driver Pack
- 解压到 `resources/vb-cable/`

### 4. 打包 Electron 应用

```bash
cd electron-app
npm run build
```

输出：`electron-app/dist/TuneHime-Setup-1.0.0.exe`

## 打包配置

### package.json 配置

```json
{
  "build": {
    "appId": "com.pkpoiw.tunehime",
    "productName": "音姬 TuneHime",
    "extraResources": [
      {
        "from": "../python-backend/dist/server.exe",
        "to": "server/server.exe"
      },
      {
        "from": "../resources/vb-cable",
        "to": "vb-cable"
      }
    ]
  }
}
```

### NSIS 安装脚本

`installer.nsh` 定义了：
- 安装时自动安装 VB-CABLE
- 创建桌面和开始菜单快捷方式
- 卸载时可选卸载 VB-CABLE

## 文件结构

```
打包后：
TuneHime-Setup-1.0.0.exe
├── resources/
│   ├── server/
│   │   └── server.exe        ← Python 后端
│   └── vb-cable/
│       ├── VBCABLE_Setup_x64.exe
│       └── ...
├── app.asar                   ← Electron 应用
└── ...
```

## 常见问题

### Q: 打包后服务器无法启动？

A: 检查 `resources/server/server.exe` 是否存在。可以手动运行测试。

### Q: VB-CABLE 安装失败？

A: 需要管理员权限。右键以管理员身份运行安装程序。

### Q: 如何测试打包后的应用？

A: 在 `electron-app/dist/` 目录中找到安装程序，双击运行即可。

### Q: 如何减小安装包大小？

A: 
- 使用 `--onefile` 模式打包 Python
- 排除不需要的 Python 模块
- 压缩资源文件

## 开发模式

开发时不需要打包，直接运行：

```bash
# 终端 1：启动 Python 后端
cd python-backend
py server.py

# 终端 2：启动 Electron 前端
cd electron-app
npm run dev
```

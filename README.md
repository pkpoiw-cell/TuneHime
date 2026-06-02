# 🎤 音姬 TuneHime

> 让每个主播都有天籁之音

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/pkpoiw/TuneHime)

**音姬**是一款专为直播主播设计的 AI 实时修音软件。一键开启，自动识别调号，智能调参，让你的声音瞬间变得专业动听。

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🎵 **AI 实时修音** | 延迟 <50ms，实时修正音高 |
| 🎯 **智能调号识别** | 自动识别歌曲调号，智能匹配 |
| 🔌 **虚拟声卡路由** | 一键连接 OBS、直播伴侣等软件 |
| 🎨 **磨砂玻璃 UI** | 粉白配色，美观易用 |
| 📦 **一键安装** | 无需复杂配置，开箱即用 |

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
cd electron-app && npm install
```

### 启动应用

```bash
# 方式一：使用启动脚本
run.bat

# 方式二：手动启动
cd python-backend
py server.py

# 新终端
cd electron-app
npm start
```

## 📖 使用指南

### 一键直播模式（推荐）

```
1. 选择你的麦克风作为输入
2. 选择输出设备（耳机或虚拟声卡）
3. 勾选"自动识别调号并自动调参"
4. 点击"一键开始直播修音"
5. 正常唱歌，软件会自动调整
```

### 连接直播软件

```
1. 安装 VB-CABLE 虚拟声卡
2. 本软件"输出"选择 CABLE Input
3. OBS/直播伴侣"麦克风"选择 CABLE Output
4. 点击"发送测试音"验证连接
```

## 🎛️ 功能详解

### 修音参数

| 参数 | 说明 | 建议值 |
|------|------|--------|
| 修音强度 | 越高越准，但可能有电音感 | 70% |
| 修音速度 | 越高越快，越低越自然 | 25% |
| 干湿比 | 修音后声音占比 | 80% |
| 噪声门 | 环境噪声大时调高 | 25% |
| 压缩 | 音量忽大忽小时调高 | 40% |
| 亮度 | 声音不够靠前时调高 | 25% |

### 内置预设

| 预设 | 场景 |
|------|------|
| 自然 | 轻修音，适合聊天、自然唱 |
| 流行 | 更稳定，适合大多数直播唱歌 |
| 电音 | 强修音，适合明显电音效果 |

## 🛠️ 技术栈

- **前端**：Electron + HTML/CSS/JS
- **后端**：Python + WebSocket
- **音频处理**：pedalboard（PitchShift、NoiseGate、Compressor 等）
- **音高检测**：YIN 算法
- **UI 设计**：磨砂玻璃风格，粉白配色

## 📁 项目结构

```
TuneHime/
├── electron-app/          # Electron 前端
│   ├── src/
│   │   ├── index.html     # 主界面
│   │   ├── js/app.js      # 前端逻辑
│   │   └── styles/        # 样式文件
│   ├── main.js            # 主进程
│   └── package.json
│
├── python-backend/        # Python 后端
│   └── server.py          # WebSocket 服务器
│
├── src/ai_live_tuner/     # 核心代码
│   ├── audio_engine.py    # 音频引擎
│   ├── dsp.py             # DSP 处理
│   └── settings.py        # 配置管理
│
└── tests/                 # 测试文件
```

## 📝 配置文件

Windows 默认路径：

```
%APPDATA%\TuneHime\settings.json    # 用户配置
%APPDATA%\TuneHime\logs\app.log     # 运行日志
```

## 🧪 运行测试

```bash
set PYTHONPATH=%cd%\src
python -m unittest discover -s tests
```

## 📦 打包发布

```bash
build_release.bat
```

输出目录：`dist\TuneHime`

## ⚠️ 当前限制

- 虚拟声卡需要用户手动安装 VB-CABLE
- 修音延迟约 43ms，专业场景建议使用 C++ 引擎
- 需要 Python 环境（计划使用 PyInstaller 打包）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 💬 联系方式

- GitHub：[@pkpoiw](https://github.com/pkpoiw)
- Issues：[提交问题](https://github.com/pkpoiw/TuneHime/issues)

---

<div align="center">
  <strong>音姬</strong> - 让每个主播都有天籁之音 🎵
</div>

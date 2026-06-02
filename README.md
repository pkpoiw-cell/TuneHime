<div align="center">

# 🎤 音姬 TuneHime

**让每个主播都有天籁之音**

[![Version](https://img.shields.io/badge/Version-V0.6-blue.svg)](https://github.com/pkpoiw-cell/TuneHime/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://github.com/pkpoiw-cell/TuneHime/releases)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 功能特点

| 功能 | 说明 |
|:-----|:-----|
| 🎵 **AI 实时修音** | 延迟 <50ms，实时修正音高 |
| 🎯 **智能调号识别** | 自动识别歌曲调号，智能匹配 |
| 🔌 **虚拟声卡路由** | 一键连接 OBS、直播伴侣等软件 |
| 📦 **开箱即用** | 无需配置 Python 环境 |

## 📥 下载

### 方式一：安装包（推荐）

下载安装程序，一键安装，自动配置虚拟声卡：

**[TuneHime-Setup-0.6.0.exe](https://github.com/pkpoiw-cell/TuneHime/releases/download/V0.6/TuneHime-Setup-0.6.0.exe)** (134 MB)

### 方式二：便携版

下载压缩包，解压后直接运行，无需安装：

> 💡 便携版需要手动安装 [VB-CABLE](https://vb-audio.com/Cable/) 才能使用虚拟声卡功能。

## 🚀 快速开始

### 安装版用户

1. 下载并运行 `TuneHime-Setup-0.6.0.exe`
2. 按照提示完成安装（可选择安装 VB-CABLE）
3. 启动音姬，开始使用

### 便携版用户

1. 下载并解压 `TuneHime-V0.6-Portable.zip`
2. 运行 `音姬 TuneHime.exe`
3. 如需虚拟声卡功能，请手动安装 VB-CABLE

## 📖 使用指南

### 一键直播模式

```
1. 选择你的麦克风作为输入
2. 选择输出设备（耳机或虚拟声卡）
3. 勾选"自动识别调号并自动调参"
4. 点击"一键开始直播修音"
5. 正常唱歌，软件会自动调整
```

### 连接直播软件

```
1. 安装 VB-CABLE 虚拟声卡（安装包版会自动安装）
2. 本软件"输出"选择 CABLE Input
3. OBS/直播伴侣"麦克风"选择 CABLE Output
4. 点击"发送测试音"验证连接
```

## 🎛️ 参数说明

| 参数 | 说明 | 建议值 |
|:-----|:-----|:-------|
| 修音强度 | 越高越准，但可能有电音感 | 70% |
| 修音速度 | 越高越快，越低越自然 | 25% |
| 干湿比 | 修音后声音占比 | 80% |
| 噪声门 | 环境噪声大时调高 | 25% |
| 压缩 | 音量忽大忽小时调高 | 40% |
| 亮度 | 声音不够靠前时调高 | 25% |

## 🛠️ 技术栈

- **前端**：Electron + HTML/CSS/JS
- **后端**：Python + WebSocket
- **音频处理**：pedalboard
- **音高检测**：YIN 算法

## 📁 项目结构

```
TuneHime/
├── electron-app/          # Electron 前端
├── python-backend/        # Python 后端
├── src/ai_live_tuner/     # 核心代码
└── resources/             # 资源文件
```

## 📋 系统要求

- Windows 10/11 (64位)
- 麦克风
- 建议 4GB 以上内存

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE)

## 🔗 相关链接

- [VB-CABLE 下载](https://vb-audio.com/Cable/)
- [问题反馈] QQ:353045258

---

<div align="center">

**音姬** - 让每个主播都有天籁之音 🎵

</div>

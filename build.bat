@echo off
chcp 65001 >nul
title 音姬 TuneHime - 完整打包工具

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           音姬 TuneHime - 完整打包工具                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [×] 错误：未找到 Python！
    echo     请安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [×] 错误：未找到 Node.js！
    echo     请安装 Node.js 16 或更高版本
    pause
    exit /b 1
)

echo [1/5] 安装 Python 依赖...
echo.
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo [√] Python 依赖已安装
echo.

echo [2/5] 安装 Node.js 依赖...
echo.
cd electron-app
call npm install --silent
echo [√] Node.js 依赖已安装
echo.

echo [3/5] 打包 Python 后端...
echo.
cd "%PROJECT_DIR%"
python build_backend.py
if errorlevel 1 (
    echo [×] Python 后端打包失败！
    pause
    exit /b 1
)
echo [√] Python 后端已打包
echo.

echo [4/5] 下载 VB-CABLE...
echo.
call download_vbcable.bat
echo [√] VB-CABLE 已准备
echo.

echo [5/5] 打包 Electron 应用...
echo.
cd electron-app
call npm run build
if errorlevel 1 (
    echo [×] Electron 打包失败！
    pause
    exit /b 1
)
echo [√] Electron 应用已打包
echo.

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    打包完成！                               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 安装包位置：
echo %PROJECT_DIR%electron-app\dist\TuneHime-Setup-1.0.0.exe
echo.
echo 文件大小：
for %%A in ("%PROJECT_DIR%electron-app\dist\TuneHime-Setup-1.0.0.exe") do echo %%~zA bytes
echo.

:: 打开输出目录
explorer "%PROJECT_DIR%electron-app\dist"

pause

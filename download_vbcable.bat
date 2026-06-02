@echo off
chcp 65001 >nul
title 下载 VB-CABLE 虚拟声卡

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           音姬 TuneHime - VB-CABLE 下载工具                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

set VB_CABLE_URL=https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip
set VB_CABLE_ZIP=%~dp0resources\vb-cable.zip
set VB_CABLE_DIR=%~dp0resources\vb-cable

:: 创建目录
if not exist "%~dp0resources" mkdir "%~dp0resources"
if not exist "%VB_CABLE_DIR%" mkdir "%VB_CABLE_DIR%"

:: 检查是否已下载
if exist "%VB_CABLE_DIR%\VBCABLE_Setup_x64.exe" (
    echo [√] VB-CABLE 已存在，跳过下载
    goto :done
)

echo [1/3] 正在下载 VB-CABLE...
echo.

:: 使用 PowerShell 下载
powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%VB_CABLE_URL%' -OutFile '%VB_CABLE_ZIP%'}"

if not exist "%VB_CABLE_ZIP%" (
    echo [×] 下载失败！
    echo.
    echo 请手动下载 VB-CABLE：
    echo %VB_CABLE_URL%
    echo.
    echo 下载后解压到：%VB_CABLE_DIR%
    pause
    exit /b 1
)

echo [√] 下载完成
echo.

echo [2/3] 正在解压...
powershell -Command "& {Expand-Archive -Path '%VB_CABLE_ZIP%' -DestinationPath '%VB_CABLE_DIR%' -Force}"

if errorlevel 1 (
    echo [×] 解压失败！
    pause
    exit /b 1
)

echo [√] 解压完成
echo.

echo [3/3] 清理临时文件...
del "%VB_CABLE_ZIP%" 2>nul
echo [√] 完成
echo.

:done
echo.
echo VB-CABLE 文件位置：%VB_CABLE_DIR%
echo.
dir "%VB_CABLE_DIR%" /b
echo.
pause

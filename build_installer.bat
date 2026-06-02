@echo off
chcp 65001 >nul
title 音姬 TuneHime - 打包安装程序

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           音姬 TuneHime - 打包安装程序                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 需要管理员权限，正在请求提升...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [√] 已获得管理员权限
echo.

cd /d "%~dp0electron-app"

echo [1/2] 清理旧的构建文件...
if exist dist rmdir /s /q dist
echo [√] 已清理
echo.

echo [2/2] 开始打包...
echo.
call npm run build

if errorlevel 1 (
    echo.
    echo [×] 打包失败！
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    打包完成！                               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 安装包位置：
dir /b "%~dp0electron-app\dist\*.exe" 2>nul
echo.

:: 打开输出目录
explorer "%~dp0electron-app\dist"

pause

@echo off
cd /d "%~dp0"
set "PYTHONPATH=%cd%\src"
set "PY_EXE=C:\Users\36956\AppData\Local\Python\bin\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo Starting AI Live Tuner...
echo.

:: Start Python backend in background
start "AI Live Tuner Backend" /MIN "%PY_EXE%" "%cd%\python-backend\server.py" 9876

:: Wait for backend to start
timeout /t 2 /nobreak >nul

:: Start Electron app
cd electron-app
npx electron .
cd ..

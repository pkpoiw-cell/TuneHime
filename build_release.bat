@echo off
setlocal
cd /d "%~dp0"
set "PY_EXE=C:\Users\36956\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"
"%PY_EXE%" -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1
set PYTHONPATH=%cd%\src
"%PY_EXE%" -m unittest discover -s tests
if errorlevel 1 exit /b 1
"%PY_EXE%" -m PyInstaller --noconfirm --clean --name "AI Live Tuner" --windowed --paths src src\ai_live_tuner\app.py
if errorlevel 1 exit /b 1
echo.
echo Build complete: %cd%\dist\AI Live Tuner

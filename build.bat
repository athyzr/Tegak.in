@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher tidak ditemukan. Install Python 3.12 64-bit beserta Python Launcher.
    exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 tidak ditemukan. Install Python 3.12 64-bit.
    exit /b 1
)

if not exist ".build-venv\Scripts\python.exe" (
    py -3.12 -m venv .build-venv
    if errorlevel 1 exit /b 1
)

".build-venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

".build-venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "Tegak-in" --collect-all mediapipe guardian.py
if errorlevel 1 exit /b 1

echo.
echo Selesai: dist\Tegak-in.exe

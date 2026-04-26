@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ====================================
echo Job Analysis Launcher
echo ====================================
echo.

set "PYTHON_EXE="
set "VENV_NAME="

if exist ".venv38\Scripts\python.exe" (
    set "PYTHON_EXE=.venv38\Scripts\python.exe"
    set "VENV_NAME=.venv38"
)

if not defined PYTHON_EXE (
    if exist "venv\Scripts\python.exe" (
        set "PYTHON_EXE=venv\Scripts\python.exe"
        set "VENV_NAME=venv"
    )
)

if not defined PYTHON_EXE (
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
        set "VENV_NAME=.venv"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] No virtual environment found.
    echo Checked: .venv38, venv, .venv
    echo Expected: .venv38
    pause
    exit /b 1
)

echo [INFO] Using virtual environment: %VENV_NAME%
for /f "delims=" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VERSION=%%i"
echo [INFO] !PY_VERSION!
echo.

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found.
    pause
    exit /b 1
)

echo [CHECK] Verifying core dependencies...
"%PYTHON_EXE%" -c "import customtkinter, openai, playwright, openpyxl" 1>nul 2>nul
if errorlevel 1 (
    echo [INSTALL] Installing or repairing dependencies...
    "%PYTHON_EXE%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo [CHECK] Verifying Playwright...
"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; print('ok')" 1>nul 2>nul
if errorlevel 1 (
    echo [ERROR] Playwright is not available.
    pause
    exit /b 1
)

echo [START] Launching application...
"%PYTHON_EXE%" main.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Application exited with code: %EXIT_CODE%
    echo Check logs\error.log
    pause
    exit /b %EXIT_CODE%
)

endlocal

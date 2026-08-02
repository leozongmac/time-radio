@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "TIME_RADIO_HOST=127.0.0.1"
set "TIME_RADIO_PORT=8766"
set "VENV_DIR=.venv-web"
set "INSTALL_MARKER=%VENV_DIR%\.time-radio-web-v1"

if not exist "%VENV_DIR%\Scripts\python.exe" (
    where uv >nul 2>nul
    if not errorlevel 1 (
        uv venv "%VENV_DIR%" --python 3.11
    ) else (
        py -3.11 -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create the Python 3.11 virtual environment.
        pause
        exit /b 1
    )
)

if not exist "%INSTALL_MARKER%" (
    echo Installing the Time Radio web environment...
    where uv >nul 2>nul
    if not errorlevel 1 (
        uv pip install --python "%VENV_DIR%" -e .
    ) else (
        "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
        if errorlevel 1 goto :install_failed
        "%VENV_DIR%\Scripts\python.exe" -m pip install -e .
    )
    if errorlevel 1 goto :install_failed
    > "%INSTALL_MARKER%" echo installed
)

"%VENV_DIR%\Scripts\python.exe" -m time_radio.launcher
if errorlevel 1 (
    echo.
    echo [ERROR] Time Radio stopped because startup failed.
    pause
    exit /b 1
)
exit /b 0

:install_failed
echo.
echo [ERROR] Dependency installation failed. Check the network and the error above.
pause
exit /b 1

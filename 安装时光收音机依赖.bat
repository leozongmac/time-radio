@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV_DIR=.venv-web"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "INSTALL_MARKER=%VENV_DIR%\.time-radio-web-v1"
set "USE_UV=0"

echo ========================================
echo   AI Time Radio - Runtime Dependency Installer
echo ========================================
echo.
echo Required: Python 3.11 or 3.12
echo This script installs runtime dependencies only.
echo.

where uv >nul 2>nul
if not errorlevel 1 set "USE_UV=1"

if not exist "%VENV_PYTHON%" (
    echo Creating the project virtual environment...
    if "%USE_UV%"=="1" (
        uv venv "%VENV_DIR%" --python 3.11
        if errorlevel 1 (
            echo [ERROR] Failed to create the Python 3.11 environment with uv.
            pause
            exit /b 1
        )
    ) else (
        where py >nul 2>nul
        if not errorlevel 1 (
            py -3.11 -m venv "%VENV_DIR%"
            if errorlevel 1 py -3.12 -m venv "%VENV_DIR%"
        ) else (
            where python >nul 2>nul
            if errorlevel 1 (
                echo [ERROR] Python 3.11 or 3.12 was not found.
                echo Install Python from https://www.python.org/downloads/windows/
                pause
                exit /b 1
            )
            python -m venv "%VENV_DIR%"
        )
        if errorlevel 1 (
            echo [ERROR] Failed to create the virtual environment.
            echo Install Python 3.11 or 3.12 and run this script again.
            pause
            exit /b 1
        )
    )
)

if not exist "%VENV_PYTHON%" (
    echo [ERROR] The virtual environment was not created correctly.
    pause
    exit /b 1
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if (sys.version_info.major, sys.version_info.minor) in ((3, 11), (3, 12)) else 1)"
if errorlevel 1 (
    echo [ERROR] .venv-web must use Python 3.11 or 3.12.
    echo Delete .venv-web and run this installer again, or recreate it with a supported Python version.
    pause
    exit /b 1
)

echo Installing the project and its runtime dependencies...
if "%USE_UV%"=="1" (
    uv pip install --python "%VENV_PYTHON%" -e .
) else (
    "%VENV_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 goto :install_failed
    "%VENV_PYTHON%" -m pip install -e .
)
if errorlevel 1 goto :install_failed

"%VENV_PYTHON%" -c "import fastapi, httpx, pydantic, uvicorn, websockets; print('Runtime dependencies imported successfully.')"
if errorlevel 1 goto :verify_failed

> "%INSTALL_MARKER%" echo installed
echo.
echo [OK] Dependencies are ready.
echo Virtual environment: %VENV_DIR%
echo Start the application with the main startup BAT file.
echo.
pause
exit /b 0

:install_failed
echo.
echo [ERROR] Dependency installation failed. Check the network and the error above.
pause
exit /b 1

:verify_failed
echo.
echo [ERROR] Dependencies were installed, but the runtime import check failed.
pause
exit /b 1

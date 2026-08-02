#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$SCRIPT_DIR"

export TIME_RADIO_HOST="127.0.0.1"
export TIME_RADIO_PORT="8766"

VENV_DIR=".venv-web"
VENV_PYTHON="$VENV_DIR/bin/python"
INSTALL_MARKER="$VENV_DIR/.time-radio-web-v1"
USE_UV=0
PYTHON_COMMAND=""

pause_on_error() {
  if [ -t 0 ]; then
    printf 'Press Enter to close...'
    IFS= read -r _ || true
  fi
}

fail() {
  printf '[ERROR] %s\n' "$1" >&2
  pause_on_error
  exit 1
}

is_supported_python() {
  "$1" -c 'import sys; raise SystemExit(0 if (sys.version_info.major, sys.version_info.minor) in ((3, 11), (3, 12)) else 1)' >/dev/null 2>&1
}

if command -v uv >/dev/null 2>&1; then
  USE_UV=1
else
  for candidate in python3.11 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && is_supported_python "$candidate"; then
      PYTHON_COMMAND="$(command -v "$candidate")"
      break
    fi
  done
  if [ -z "$PYTHON_COMMAND" ]; then
    fail 'Python 3.11 or 3.12 is required. Install Python from https://www.python.org/downloads/macos/.'
  fi
fi

if [ ! -x "$VENV_PYTHON" ]; then
  printf 'Creating the project virtual environment...\n'
  if [ "$USE_UV" -eq 1 ]; then
    if ! uv venv "$VENV_DIR" --python 3.11; then
      fail 'Could not create .venv-web with uv. Check the network or install Python 3.11/3.12.'
    fi
  elif ! "$PYTHON_COMMAND" -m venv "$VENV_DIR"; then
    fail 'Could not create .venv-web. Check that the selected Python installation includes venv.'
  fi
fi

if [ ! -x "$VENV_PYTHON" ]; then
  fail 'The .venv-web environment was not created correctly.'
fi

if ! is_supported_python "$VENV_PYTHON"; then
  fail '.venv-web must use Python 3.11 or 3.12. Remove .venv-web and run this script again.'
fi

if [ ! -f "$INSTALL_MARKER" ]; then
  printf 'Installing the Time Radio web environment...\n'
  if [ "$USE_UV" -eq 1 ]; then
    if ! uv pip install --python "$VENV_PYTHON" -e .; then
      fail 'Dependency installation failed. Check the network and the error above.'
    fi
  else
    if ! "$VENV_PYTHON" -m pip install --upgrade pip; then
      fail 'pip could not be upgraded. Check the network and the error above.'
    fi
    if ! "$VENV_PYTHON" -m pip install -e .; then
      fail 'Dependency installation failed. Check the network and the error above.'
    fi
  fi
  if ! "$VENV_PYTHON" -c 'import fastapi, httpx, pydantic, uvicorn, websockets'; then
    fail 'Runtime dependency verification failed after installation.'
  fi
  printf 'installed\n' > "$INSTALL_MARKER"
fi

if ! "$VENV_PYTHON" -c 'import fastapi, httpx, pydantic, uvicorn, websockets' >/dev/null 2>&1; then
  fail 'Runtime dependencies are incomplete. Run this script again to repair .venv-web.'
fi

printf 'Time Radio is starting at http://%s:%s\n' "$TIME_RADIO_HOST" "$TIME_RADIO_PORT"
if ! "$VENV_PYTHON" -m time_radio.launcher; then
  fail 'Time Radio stopped unexpectedly. Check the error above and whether port 8766 is already in use.'
fi

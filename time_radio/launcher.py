from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser

import httpx
import uvicorn


def require_available_port(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1.0)
        result = probe.connect_ex((host, port))
    if result == 0:
        raise RuntimeError(
            f"Time Radio cannot start because {host}:{port} is already in use. "
            "Close the process using that port or set TIME_RADIO_PORT to another port."
        )


def wait_for_server_and_open(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{url}/api/health", timeout=1.0)
            if response.status_code == 200:
                webbrowser.open(url, new=2)
                return
        except httpx.RequestError:
            time.sleep(0.35)
    print(f"Time Radio started, but the browser did not open automatically. Open {url} manually.")


def main() -> None:
    host = os.environ.get("TIME_RADIO_HOST", "127.0.0.1")
    port = int(os.environ.get("TIME_RADIO_PORT", "8766"))
    require_available_port(host, port)
    url = f"http://{host}:{port}"
    browser_thread = threading.Thread(
        target=wait_for_server_and_open,
        args=(url, 30.0),
        daemon=True,
    )
    browser_thread.start()
    print(f"Time Radio is starting at {url}")
    uvicorn.run(
        "time_radio.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

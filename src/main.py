"""Application entry point: starts FastAPI and pywebview desktop window."""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Ensure src is on path when running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.routes import router
from src.core.config import settings


def find_free_port(host: str = "127.0.0.1", start: int = 18080) -> int:
    """Find a free TCP port starting from `start`."""
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) != 0:
                return port
            port += 1


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="OCR Alliance API", version="0.1.0")
    app.include_router(router, prefix="/api")

    web_dir = Path(__file__).resolve().parent / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")

    return app


def run_server(host: str, port: int) -> None:
    """Run uvicorn server in a background thread."""
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)


def _run_webview(url: str) -> bool:
    """Try to open a pywebview desktop window. Return True on success."""
    try:
        import webview
    except Exception as exc:  # noqa: BLE001
        print(f"pywebview import failed: {exc}")
        return False

    try:
        window = webview.create_window(
            title=settings.window_title,
            url=url,
            width=settings.window_width,
            height=settings.window_height,
            min_size=(1000, 700),
        )

        def get_platform() -> str:
            return settings.platform

        def open_external(target_url: str) -> None:
            webbrowser.open(target_url)

        window.expose(get_platform, open_external)
        webview.start(debug=False)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"pywebview start failed: {exc}")
        return False


def _run_browser_fallback(url: str) -> None:
    """Open the app in the system default browser and keep the server alive."""
    print("Falling back to system default browser.")
    webbrowser.open(url)
    print(f"OCR Alliance is running in your browser at {url}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")


def main() -> None:
    """Entry point: ensure dirs, start server, open webview or browser."""
    settings.ensure_dirs()

    host = settings.api_host
    port = settings.api_port or find_free_port(host)

    server_thread = threading.Thread(
        target=run_server,
        args=(host, port),
        daemon=True,
    )
    server_thread.start()

    url = f"http://{host}:{port}"
    print(f"OCR Alliance server started at {url}")

    if not _run_webview(url):
        _run_browser_fallback(url)


if __name__ == "__main__":
    main()

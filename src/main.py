"""Application entry point: starts FastAPI and pywebview desktop window."""

from __future__ import annotations

import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
import webview
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


def main() -> None:
    """Entry point: ensure dirs, start server, open webview."""
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

    window = webview.create_window(
        title=settings.window_title,
        url=url,
        width=settings.window_width,
        height=settings.window_height,
        min_size=(1000, 700),
    )

    # Expose settings and platform info to frontend via pywebview
    def get_platform() -> str:
        return settings.platform

    def open_external(url: str) -> None:
        webbrowser.open(url)

    window.expose(get_platform, open_external)

    webview.start(debug=False)


if __name__ == "__main__":
    main()

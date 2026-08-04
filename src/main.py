"""Application entry point: starts FastAPI and pywebview desktop window."""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import traceback
import urllib.request
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
from src.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


def find_free_port(host: str = "127.0.0.1", start: int = 18080) -> int:
    """Find a free TCP port starting from `start`."""
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) != 0:
                return port
            port += 1


def _resolve_web_dir() -> Path:
    """Return the directory containing the bundled web assets."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "web"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "web"


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="OCR Alliance API", version="0.1.0")
    app.include_router(router, prefix="/api")

    web_dir = _resolve_web_dir()
    logger.info("Static files directory: %s (exists=%s)", web_dir, web_dir.is_dir())
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    else:
        logger.warning("Static files directory not found; web UI will not be served")

    return app


def run_server(host: str, port: int) -> None:
    """Run uvicorn server in a background thread."""
    app = create_app()
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
            log_config=None,
            loop="asyncio",
        )
    except Exception:
        logger.exception("Uvicorn server failed")
        raise


def wait_for_server(base_url: str, timeout: float = 10.0) -> bool:
    """Wait until the local server is accepting API requests."""
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/settings", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(0.2)
    logger.warning("Server readiness check timed out: %s", last_error)
    return False


def _run_webview(url: str) -> bool:
    """Try to open a pywebview desktop window. Return True on success."""
    try:
        import webview
    except Exception as exc:  # noqa: BLE001
        logger.warning("pywebview import failed: %s", exc)
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
        logger.warning("pywebview start failed: %s", exc)
        return False


def _run_browser_fallback(url: str) -> None:
    """Open the app in the system default browser and keep the server alive."""
    logger.info("Falling back to system default browser.")
    webbrowser.open(url)
    logger.info("OCR Alliance is running in your browser at %s", url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down.")


def main() -> None:
    """Entry point: ensure dirs, start server, open webview or browser."""
    setup_logging()

    try:
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
        logger.info("OCR Alliance server starting at %s", url)

        if not wait_for_server(url):
            logger.error("Server did not become ready within timeout")
            return

        logger.info("OCR Alliance server is ready at %s", url)

        if not _run_webview(url):
            _run_browser_fallback(url)
    except Exception:
        logger.exception("Fatal error during startup")
        # Print to stderr as a last resort in case logging failed.
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

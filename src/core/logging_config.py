"""Persistent file logging setup for OCR Alliance."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

from src.core.config import settings


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def setup_logging() -> logging.Handler | None:
    """Configure logging to a rotating file and optionally the console.

    Returns the file handler so callers can flush it explicitly if needed.
    """
    settings.ensure_dirs()
    log_path = settings.data_dir / "ocr_alliance.log"

    handlers: list[logging.Handler] = []

    file_handler = logging.handlers.RotatingFileHandler(
        str(log_path),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handlers.append(file_handler)

    # Keep console output when running from source or when explicitly requested.
    if not _is_frozen() or os.environ.get("OCR_ALLIANCE_CONSOLE_LOG") == "1":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(console_handler)

    level = logging.DEBUG if os.environ.get("DEBUG") == "1" else logging.INFO
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Log file: %s", log_path)
    logger.info("Running from source: %s", not _is_frozen())
    return file_handler

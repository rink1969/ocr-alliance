"""Utilities for reading and updating the .env configuration file."""

from __future__ import annotations

from pathlib import Path

from src.core.config import settings


def env_file_path() -> Path:
    """Return the path to the .env file used by the application."""
    return settings.app_root / ".env"


def read_env() -> dict[str, str]:
    """Read the .env file into a dictionary.

    Missing or malformed lines are ignored.
    """
    path = env_file_path()
    if not path.is_file():
        return {}

    result: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def update_env(updates: dict[str, str]) -> None:
    """Update the .env file with the provided key/value pairs.

    Existing keys are overwritten; missing keys are appended. The file is
    created if it does not exist.
    """
    path = env_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    env_vars = read_env()
    env_vars.update(updates)

    lines: list[str] = []
    for key, value in env_vars.items():
        lines.append(f"{key}={value}\n")

    with path.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def mask_api_key(key: str) -> str:
    """Return a masked representation of an API key.

    Shows the first 4 and last 4 characters when possible; otherwise returns
    a fixed mask string.
    """
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"

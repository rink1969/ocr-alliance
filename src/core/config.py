"""Application configuration."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_app_root() -> Path:
    """Return the project root.

    When running inside a PyInstaller bundle, use the directory containing
    the executable so user data lives next to the app instead of inside the
    frozen _internal folder.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Runtime settings for OCR Alliance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application paths
    app_root: Path = _resolve_app_root()
    data_dir: Path = app_root / "data"
    models_dir: Path = app_root / "models"
    db_path: Path = data_dir / "ocr_alliance.db"

    # API server
    api_host: str = "127.0.0.1"
    api_port: int = 0  # 0 means auto-assign an available port

    # UI
    window_title: str = "OCR Alliance"
    window_width: int = 1400
    window_height: int = 900

    # OCR
    image_extensions: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tiff",
        ".tif",
    )
    output_suffixes: dict[str, str] = {
        "paddleocr": ".paddleocr.txt",
        "hunyuan": ".hunyuan.txt",
        "glm": ".glm.txt",
        "unified": ".unified.txt",
    }

    # Model directories
    @property
    def paddleocr_model_dir(self) -> Path:
        return self.models_dir / "paddleocr-vl-1.6"

    @property
    def hunyuan_model_dir(self) -> Path:
        return self.models_dir / "hunyuanocr"

    @property
    def glm_model_dir(self) -> Path:
        return self.models_dir / "glm-ocr"

    # Model download
    auto_download_models: bool = True

    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    llm_temperature: float = 0.0
    llm_max_tokens: int = 8192
    llm_timeout: float = 120.0

    @property
    def platform(self) -> str:
        """Return the current platform identifier."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        if system == "darwin":
            return "macos"
        if system == "windows":
            return "windows"
        return machine if system == "linux" else system

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("paddleocr-vl-1.6", "hunyuanocr", "glm-ocr"):
            (self.models_dir / sub).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

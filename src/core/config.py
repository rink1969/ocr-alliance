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
        "rapidocr": ".rapidocr.txt",
        "hunyuan": ".hunyuan.txt",
        "glm": ".glm.txt",
        "unified": ".unified.txt",
    }

    # Model directories
    @property
    def rapidocr_model_dir(self) -> Path:
        return self.models_dir / "rapidocr"

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

    def _coerce_field(self, field_name: str, raw: str) -> object:
        """Convert a raw string value to the field's declared type."""
        annotation = self.__class__.model_fields[field_name].annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            args = getattr(annotation, "__args__", ())
            for arg in args:
                if arg is not type(None):
                    annotation = arg
                    break
        if annotation is int:
            return int(raw)
        if annotation is float:
            return float(raw)
        if annotation is bool:
            return raw.lower() in ("true", "1", "yes", "on")
        return raw

    def reload(self) -> None:
        """Reload settings from the .env file managed by settings_manager."""
        from src.core.settings_manager import read_env

        env_to_field = {
            "API_HOST": "api_host",
            "API_PORT": "api_port",
            "AUTO_DOWNLOAD_MODELS": "auto_download_models",
            "LLM_BASE_URL": "llm_base_url",
            "LLM_MODEL": "llm_model",
            "LLM_API_KEY": "llm_api_key",
            "LLM_TEMPERATURE": "llm_temperature",
            "LLM_MAX_TOKENS": "llm_max_tokens",
            "LLM_TIMEOUT": "llm_timeout",
        }
        env_vars = read_env()
        for env_name, field_name in env_to_field.items():
            if env_name in env_vars:
                setattr(self, field_name, self._coerce_field(field_name, env_vars[env_name]))

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("rapidocr", "hunyuanocr", "glm-ocr"):
            (self.models_dir / sub).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

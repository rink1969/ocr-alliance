"""OCR model download manager using ModelScope."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)

MODEL_REPOS: dict[str, str] = {
    "rapidocr": "RapidAI/RapidOCR",
    "hunyuan": "Tencent-Hunyuan/HunyuanOCR",
    "glm": "ZhipuAI/GLM-OCR",
}

WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pth", ".ckpt", ".pt")


class DownloadStatus(str, Enum):
    """Possible states for a model download."""

    READY = "ready"
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    ERROR = "error"


@dataclass
class ModelState:
    """Download state for a single model."""

    name: str
    status: DownloadStatus = DownloadStatus.PENDING
    message: str = ""
    downloaded_bytes: int = 0
    total_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
        }


class _FileProgress:
    def __init__(
        self, name: str, manager: ModelManager, filename: str, file_size: int
    ) -> None:
        self.name = name
        self.manager = manager
        self.filename = filename
        self.file_size = file_size
        self._seen = 0

    def update(self, size: int) -> None:
        self._seen = size
        self.manager._update_file_progress(
            self.name, self.filename, self.file_size, size
        )

    def end(self) -> None:
        pass


def _make_progress_callback_class(name: str, manager: ModelManager) -> type:
    """Create a ModelScope ProgressCallback subclass bound to this model."""
    from modelscope.hub.callback import ProgressCallback

    class _Callback(ProgressCallback):
        def __init__(self, filename: str, file_size: int) -> None:
            super().__init__(filename, file_size)
            self._progress = _FileProgress(name, manager, filename, file_size)

        def update(self, size: int) -> None:
            self._progress.update(size)

        def end(self) -> None:
            self._progress.end()

    return _Callback


class ModelManager:
    """Detect missing OCR models and download them from ModelScope."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, ModelState] = {
            name: ModelState(name=name) for name in MODEL_REPOS
        }
        self._threads: dict[str, threading.Thread] = {}
        self._file_progress: dict[str, dict[str, tuple[int, int]]] = {}

    def model_dir(self, name: str) -> Path:
        """Return the local directory for a given model."""
        mapping = {
            "rapidocr": settings.rapidocr_model_dir,
            "hunyuan": settings.hunyuan_model_dir,
            "glm": settings.glm_model_dir,
        }
        if name not in mapping:
            raise ValueError(f"Unknown model: {name}")
        return mapping[name]

    def is_model_ready(self, name: str) -> bool:
        """Return True when the model directory contains a config and weights."""
        # RapidOCR bundles its own models inside the package; no local
        # download directory is required.
        if name == "rapidocr":
            return True

        directory = self.model_dir(name)
        if not directory.is_dir():
            return False

        has_config = (directory / "config.json").is_file()
        has_weights = any(
            path.is_file() and path.suffix.lower() in WEIGHT_SUFFIXES
            for path in directory.rglob("*")
        )
        return has_config and has_weights

    def get_status(self) -> list[ModelState]:
        """Return the current status of all models."""
        with self._lock:
            for state in self._states.values():
                if state.status != DownloadStatus.READY and self.is_model_ready(state.name):
                    state.status = DownloadStatus.READY
                    state.message = "模型已就绪"
            return list(self._states.values())

    def all_ready(self) -> bool:
        """Return True when every model is present locally."""
        return all(self.is_model_ready(name) for name in MODEL_REPOS)

    def _update_state(
        self,
        name: str,
        status: DownloadStatus,
        message: str = "",
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> None:
        with self._lock:
            state = self._states[name]
            state.status = status
            if message:
                state.message = message
            if downloaded_bytes is not None:
                state.downloaded_bytes = downloaded_bytes
            if total_bytes is not None:
                state.total_bytes = total_bytes

    def _update_file_progress(
        self, name: str, filename: str, file_size: int, downloaded: int
    ) -> None:
        """Update aggregate progress for an active download.

        ``_file_progress`` maps ``model_name -> {filename: (file_size, downloaded)}``.
        The aggregate ``downloaded_bytes`` and ``total_bytes`` are recomputed on
        every update so that the UI can show real progress even when multiple
        files are downloaded concurrently.
        """
        with self._lock:
            files = self._file_progress.setdefault(name, {})
            files[filename] = (file_size, downloaded)
            total = sum(size for size, _ in files.values())
            done = sum(dl for _, dl in files.values())
            self._states[name].total_bytes = total
            self._states[name].downloaded_bytes = done

    def _download(self, name: str) -> None:
        """Download a single model in a background thread."""
        repo_id = MODEL_REPOS[name]
        local_dir = self.model_dir(name)
        local_dir.mkdir(parents=True, exist_ok=True)

        self._update_state(
            name,
            DownloadStatus.DOWNLOADING,
            f"正在从 {repo_id} 下载...",
            downloaded_bytes=0,
            total_bytes=None,
        )
        logger.info("Downloading model %s from %s to %s", name, repo_id, local_dir)

        try:
            from modelscope.hub.snapshot_download import snapshot_download

            callback_cls = _make_progress_callback_class(name, self)
            snapshot_download(
                repo_id,
                local_dir=str(local_dir),
                progress_callbacks=[callback_cls],
            )
            if self.is_model_ready(name):
                self._update_state(name, DownloadStatus.DONE, "下载完成")
                logger.info("Model %s download complete", name)
            else:
                self._update_state(
                    name,
                    DownloadStatus.ERROR,
                    "下载完成但未找到有效的模型文件",
                )
        except Exception as exc:
            error = str(exc)
            self._update_state(name, DownloadStatus.ERROR, f"下载失败: {error}")
            logger.exception("Model %s download failed", name)

    def start_download(self, name: str) -> bool:
        """Start downloading a model if it is not already ready or downloading."""
        if name not in MODEL_REPOS:
            return False

        with self._lock:
            if self.is_model_ready(name):
                self._states[name].status = DownloadStatus.READY
                return True
            existing = self._threads.get(name)
            if existing and existing.is_alive():
                return True

        thread = threading.Thread(target=self._download, args=(name,), daemon=True)
        with self._lock:
            self._threads[name] = thread
        thread.start()
        return True

    def start_missing_downloads(self) -> list[str]:
        """Start downloads for all models that are not ready."""
        started: list[str] = []
        for name in MODEL_REPOS:
            if not self.is_model_ready(name) and self.start_download(name):
                started.append(name)
        return started

    def get_progress(self) -> list[dict[str, Any]]:
        """Return progress info for all models."""
        return [state.to_dict() for state in self.get_status()]


# Global model manager instance
model_manager = ModelManager()

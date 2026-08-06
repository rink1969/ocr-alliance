"""Batch processing scheduler."""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.core.database import Task, TaskStatus, db
from src.core.file_utils import output_path_for
from src.llm.unifier import LLMUnifier, OCRInputs
from src.ocr.registry import get_ocr_adapters

logger = logging.getLogger(__name__)


class ProcessingState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"


class Scheduler:
    """Simple background scheduler for OCR batch processing."""

    def __init__(self) -> None:
        self.state = ProcessingState.IDLE
        self.input_dir: str = ""
        self.output_dir: str = ""
        self.current_file: str = ""
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._unifier = LLMUnifier()

    def start(self, input_dir: str, output_dir: str) -> None:
        """Start background processing thread."""
        if self.state == ProcessingState.RUNNING:
            return

        self.input_dir = input_dir
        self.output_dir = output_dir
        # Reset tasks left in 'processing' from a previous run so they are
        # picked up again instead of being stranded.
        db.reset_incomplete(input_dir, output_dir)
        self._stop_event.clear()
        self.state = ProcessingState.RUNNING
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal scheduler to stop."""
        if self.state != ProcessingState.RUNNING:
            return
        self.state = ProcessingState.STOPPING
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.state = ProcessingState.IDLE

    def _run(self) -> None:
        """Main processing loop."""
        try:
            while not self._stop_event.is_set():
                tasks = db.list_tasks(
                    input_path=self.input_dir,
                    output_dir=self.output_dir,
                    status=TaskStatus.PENDING,
                )
                if not tasks:
                    break

                task = tasks[0]
                self.current_file = task.relative_path
                db.update_task_status(task.id, TaskStatus.PROCESSING)

                try:
                    results = self._process_task(task)
                    db.update_task_status(task.id, TaskStatus.DONE, results_json=results)
                except Exception as exc:
                    logger.exception("Task failed: %s", task.relative_path)
                    db.update_task_status(task.id, TaskStatus.FAILED, error=str(exc))

                time.sleep(0.1)
        finally:
            self.state = ProcessingState.IDLE
            self.current_file = ""

    def _locate_image(self, task: Task) -> Path:
        """Find the source image for a task."""
        image_path = Path(task.input_path) / task.relative_path
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found for task: {task.relative_path}")
        return image_path

    def _process_task(self, task: Task) -> dict[str, Any]:
        """Run OCR adapters and the LLM unifier for a single task."""
        image_path = self._locate_image(task)
        output_dir = Path(task.output_dir)

        ocr_inputs = OCRInputs()
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for adapter in get_ocr_adapters():
            suffix = settings.output_suffixes.get(adapter.name)
            if suffix is None:
                continue

            output_path = output_path_for(
                task.input_path, output_dir, image_path, suffix
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if not adapter.available:
                hint = adapter.setup_hint()
                output_path.write_text(hint, encoding="utf-8")
                results[adapter.name] = ""
                errors[adapter.name] = hint
                setattr(ocr_inputs, adapter.name, "")
                logger.warning("OCR adapter %s not available: %s", adapter.name, hint)
                continue

            try:
                text = adapter.recognize(image_path)
                output_path.write_text(text, encoding="utf-8")
                results[adapter.name] = text
                setattr(ocr_inputs, adapter.name, text)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                output_path.write_text(f"识别失败: {error}", encoding="utf-8")
                results[adapter.name] = ""
                errors[adapter.name] = error
                setattr(ocr_inputs, adapter.name, "")
                logger.warning("OCR adapter %s failed: %s", adapter.name, error)

        available = [text for text in ocr_inputs.__dict__.values() if text]
        if not available:
            raise RuntimeError("没有可用的 OCR 结果，无法进行 LLM 统合")

        unified_text = self._unifier.unify(image_path, ocr_inputs)
        unified_path = output_path_for(
            task.input_path, output_dir, image_path, settings.output_suffixes["unified"]
        )
        unified_path.write_text(unified_text, encoding="utf-8")
        results["unified"] = unified_text
        if errors:
            results["_errors"] = errors

        return results


# Global scheduler instance
scheduler = Scheduler()

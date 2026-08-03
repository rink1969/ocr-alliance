"""End-to-end smoke test for the OCR + LLM pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.core.database import Database, TaskStatus
from src.core.file_utils import ensure_output_dirs, scan_images
from src.core.scheduler import Scheduler
from src.ocr.base import OCRAdapter


class MockOCRAdapter(OCRAdapter):
    """Fake OCR adapter for testing."""

    name = "paddleocr"
    display_name = "Mock OCR"

    def __init__(self, text: str) -> None:
        self.text = text

    @property
    def available(self) -> bool:
        return True

    def recognize(self, image_path: Path) -> str:
        return self.text


def test_scheduler_processes_image_and_writes_outputs() -> None:
    """Verify the scheduler runs OCR adapters and writes all result files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)

        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        input_dir.mkdir()

        img_path = input_dir / "page1.png"
        Image.new("RGB", (100, 50), color="white").save(img_path)

        images = scan_images(input_dir)
        ensure_output_dirs(input_dir, output_dir, images)

        from src.core.file_utils import relative_path

        rel = relative_path(input_dir, img_path)
        task = db.upsert_task(
            input_path=str(input_dir),
            output_dir=str(output_dir),
            relative_path=rel,
        )
        assert task is not None

        mock_text = "测试文字\n第二行"
        unified_text = "统合后的文字"

        scheduler = Scheduler()
        with (
            patch("src.core.scheduler.get_ocr_adapters", return_value=[MockOCRAdapter(mock_text)]),
            patch("src.core.scheduler.db", db),
            patch.object(scheduler._unifier, "unify", return_value=unified_text),
        ):
            scheduler._run()

        task = db.get_task(str(input_dir), str(output_dir), rel)
        assert task is not None
        assert task.status == TaskStatus.DONE
        assert task.results_json.get("paddleocr") == mock_text
        assert task.results_json.get("unified") == unified_text

        paddle_path = output_dir / (img_path.stem + ".paddleocr.txt")
        unified_path = output_dir / (img_path.stem + ".unified.txt")
        assert paddle_path.read_text(encoding="utf-8") == mock_text
        assert unified_path.read_text(encoding="utf-8") == unified_text

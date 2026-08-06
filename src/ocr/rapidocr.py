"""RapidOCR adapter.

RapidOCR is a lightweight, offline, cross-platform OCR engine based on ONNX
Runtime. It is used here as a fast, dependency-light alternative to the
heavier PaddleOCR-VL-1.6 model.
"""

from __future__ import annotations

from pathlib import Path

from src.ocr.base import OCRAdapter


class RapidOCRAdapter(OCRAdapter):
    """RapidOCR adapter.

    The adapter uses the ``rapidocr`` Python package, which bundles its own
    default ONNX models and downloads them automatically on first use. No extra
    model directory is required.
    """

    name = "rapidocr"
    display_name = "RapidOCR"

    def __init__(self) -> None:
        self._engine: object | None = None

    @property
    def available(self) -> bool:
        try:
            from rapidocr import RapidOCR  # noqa: F401
        except ImportError:
            return False
        return True

    def setup_hint(self) -> str:
        return (
            "RapidOCR 未安装。请执行：pip install 'rapidocr>=3.0.0' "
            "并确保 onnxruntime 可用。"
        )

    def _get_engine(self) -> object:
        if self._engine is None:
            from rapidocr import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def recognize(self, image_path: Path) -> str:
        engine = self._get_engine()
        result = engine(str(image_path))

        if not result or result.txts is None or len(result.txts) == 0:
            return ""

        # Join detected text boxes with newlines, preserving reading order.
        return "\n".join(str(line) for line in result.txts)

"""Registry of built-in OCR adapters."""

from __future__ import annotations

from src.ocr.base import OCRAdapter
from src.ocr.glm import GLMOCRAdapter
from src.ocr.hunyuan import HunyuanOCRAdapter
from src.ocr.rapidocr import RapidOCRAdapter


def get_ocr_adapters() -> list[OCRAdapter]:
    """Return all OCR adapters in the order they should be executed."""
    return [
        RapidOCRAdapter(),
        HunyuanOCRAdapter(),
        GLMOCRAdapter(),
    ]


def get_adapter_names() -> list[str]:
    """Return adapter names matching ``settings.output_suffixes`` keys."""
    return [adapter.name for adapter in get_ocr_adapters()]

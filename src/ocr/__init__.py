"""OCR engine adapters."""

from src.ocr.base import OCRAdapter
from src.ocr.registry import get_ocr_adapters

__all__ = ["OCRAdapter", "get_ocr_adapters"]

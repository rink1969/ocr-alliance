"""Base class for OCR engine adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class OCRAdapter(ABC):
    """Abstract adapter for a single OCR engine."""

    name: str = ""
    display_name: str = ""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Return True when the engine can be used on this machine."""
        ...

    @abstractmethod
    def recognize(self, image_path: Path) -> str:
        """Run OCR on ``image_path`` and return the recognized text.

        Raises:
            RuntimeError: when the engine is available but fails to recognize the image.
        """
        ...

    def setup_hint(self) -> str:
        """Human-readable hint for making this engine available."""
        return f"模型 {self.display_name} 尚未配置或不可用。"

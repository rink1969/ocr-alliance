"""HunyuanOCR adapter.

This adapter loads the model from ``settings.hunyuan_model_dir`` when it
contains recognisable Hugging Face model files. Otherwise it reports that the
model needs to be downloaded.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config import settings
from src.ocr.base import OCRAdapter

logger = logging.getLogger(__name__)


class HunyuanOCRAdapter(OCRAdapter):
    """HunyuanOCR adapter."""

    name = "hunyuan"
    display_name = "HunyuanOCR"

    def __init__(self) -> None:
        self._processor: object | None = None
        self._model: object | None = None

    @property
    def available(self) -> bool:
        try:
            import transformers  # noqa: F401
        except ImportError:
            return False
        return self._has_model_files()

    def setup_hint(self) -> str:
        return (
            "HunyuanOCR 模型未找到。请将 Hugging Face 上的 HunyuanOCR "
            f"模型文件下载到 {settings.hunyuan_model_dir}"
        )

    def _has_model_files(self) -> bool:
        model_dir = settings.hunyuan_model_dir
        return model_dir.is_dir() and any(
            (model_dir / name).exists()
            for name in ("config.json", "pytorch_model.bin", "model.safetensors")
        )

    def recognize(self, image_path: Path) -> str:
        if not self._has_model_files():
            raise RuntimeError(self.setup_hint())

        from PIL import Image

        if self._processor is None or self._model is None:
            # Try the dedicated HunyuanVL class first; fall back to the generic
            # Auto classes if the checkpoint does not expose it.
            try:
                from transformers import (
                    HunyuanProcessor,
                    HunYuanVLForConditionalGeneration,
                )

                self._processor = HunyuanProcessor.from_pretrained(
                    str(settings.hunyuan_model_dir), trust_remote_code=True
                )
                self._model = HunYuanVLForConditionalGeneration.from_pretrained(
                    str(settings.hunyuan_model_dir),
                    trust_remote_code=True,
                    device_map="auto",
                )
            except (ImportError, AttributeError, ValueError) as first_exc:
                logger.warning(
                    "HunyuanVL dedicated class not available (%s), trying Auto classes",
                    first_exc,
                )
                from transformers import AutoModelForVision2Seq, AutoProcessor

                self._processor = AutoProcessor.from_pretrained(
                    str(settings.hunyuan_model_dir), trust_remote_code=True
                )
                self._model = AutoModelForVision2Seq.from_pretrained(
                    str(settings.hunyuan_model_dir),
                    trust_remote_code=True,
                    device_map="auto",
                )

        image = Image.open(image_path).convert("RGB")
        prompt = "识别图片中的全部文字，保留排版："
        inputs = self._processor(images=image, text=prompt, return_tensors="pt")
        inputs = inputs.to(self._model.device)
        outputs = self._model.generate(**inputs, max_new_tokens=4096)
        text = self._processor.batch_decode(outputs, skip_special_tokens=True)[0]
        return text

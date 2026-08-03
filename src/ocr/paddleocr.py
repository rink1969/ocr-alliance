"""PaddleOCR-VL-1.6 adapter.

PaddleOCR-VL-1.6 is a 0.9B vision-language model distributed on HuggingFace /
ModelScope and loaded via ``transformers``.
"""

from __future__ import annotations

from pathlib import Path

from src.core.config import settings
from src.ocr.base import OCRAdapter


class PaddleOCRAdapter(OCRAdapter):
    """PaddleOCR-VL-1.6 adapter."""

    name = "paddleocr"
    display_name = "PaddleOCR-VL-1.6"

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
            "PaddleOCR-VL-1.6 模型未找到。请从 HuggingFace "
            "(PaddlePaddle/PaddleOCR-VL-1.6) 或魔搭社区下载模型文件到 "
            f"{settings.paddleocr_model_dir}"
        )

    def _has_model_files(self) -> bool:
        model_dir = settings.paddleocr_model_dir
        return model_dir.is_dir() and any(
            (model_dir / name).exists()
            for name in ("config.json", "pytorch_model.bin", "model.safetensors")
        )

    def recognize(self, image_path: Path) -> str:
        if not self._has_model_files():
            raise RuntimeError(self.setup_hint())

        from PIL import Image
        from transformers import AutoModelForVision2Seq, AutoProcessor

        if self._processor is None or self._model is None:
            self._processor = AutoProcessor.from_pretrained(
                str(settings.paddleocr_model_dir), trust_remote_code=True
            )
            self._model = AutoModelForVision2Seq.from_pretrained(
                str(settings.paddleocr_model_dir),
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

"""LLM-based unification of multiple OCR results."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OCRInputs:
    """OCR results from the three engines."""

    rapidocr: str = ""
    hunyuan: str = ""
    glm: str = ""


class LLMUnifier:
    """Combine multiple OCR outputs into a single best-effort text using an LLM."""

    def __init__(self) -> None:
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai 包未安装，无法调用大语言模型") from exc

            self._client = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key or "no-api-key",
                timeout=settings.llm_timeout,
            )
        return self._client

    @staticmethod
    def _build_prompt(image_name: str, inputs: OCRInputs) -> str:
        sections = []
        if inputs.rapidocr:
            sections.append(f"【RapidOCR 识别结果】\n{inputs.rapidocr}")
        if inputs.hunyuan:
            sections.append(f"【HunyuanOCR 识别结果】\n{inputs.hunyuan}")
        if inputs.glm:
            sections.append(f"【GLM-OCR 识别结果】\n{inputs.glm}")

        if not sections:
            return ""

        joined = "\n\n".join(sections)
        return (
            "你是一位专业的文档校对专家。下面是一张图片 "
            f"「{image_name}」经由三个不同 OCR 引擎识别出的文本。"
            "请综合比较这些结果，输出一份最准确、最完整的最终文本。"
            "保留原始排版（段落、换行、列表），修正明显的错字和漏字，"
            "但不要添加原文中不存在的内容。如果各引擎结果不一致，"
            "请选择最合理、最符合上下文的那一项。\n\n"
            f"{joined}\n\n"
            "请直接输出最终文本，不要包含解释。"
        )

    def unify(self, image_path: Path, inputs: OCRInputs) -> str:
        """Call the configured LLM and return the unified text."""
        prompt = self._build_prompt(image_path.name, inputs)
        if not prompt:
            raise RuntimeError("没有可用的 OCR 结果用于统合")

        client = self._get_client()
        max_retries = 3
        base_delay = 1.0
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的 OCR 后处理助手。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "LLM unification failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)

        raise RuntimeError(f"LLM 统合失败，已重试 {max_retries} 次: {last_error}")

"""Tests for the model download manager."""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.core.model_manager import ModelManager


def test_model_manager_detects_missing_models() -> None:
    """A fresh manager should report RapidOCR as ready and VLM models as missing."""
    with tempfile.TemporaryDirectory():
        manager = ModelManager()

        # RapidOCR bundles its own models; it is always considered ready.
        assert manager.is_model_ready("rapidocr")
        # The Hunyuan / GLM directories do not exist yet.
        assert not manager.is_model_ready("hunyuan")
        assert not manager.is_model_ready("glm")
        assert not manager.all_ready()


def test_model_manager_detects_ready_model() -> None:
    """is_model_ready returns True when config.json and weights exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ModelManager()
        model_dir = Path(tmpdir) / "hunyuanocr"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        (model_dir / "model.safetensors").write_text("weights", encoding="utf-8")

        # Patch the mapping for this test
        original_dir = manager.model_dir

        def patched_dir(name: str) -> Path:
            return model_dir if name == "hunyuan" else original_dir(name)

        manager.model_dir = patched_dir  # type: ignore[method-assign]

        assert manager.is_model_ready("hunyuan")
        assert not manager.is_model_ready("glm")

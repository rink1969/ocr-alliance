"""Tests for the model download manager."""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.core.model_manager import MODEL_REPOS, ModelManager


def test_model_manager_detects_missing_models() -> None:
    """A fresh manager should report all models as missing."""
    with tempfile.TemporaryDirectory():
        manager = ModelManager()

        # Directories do not exist yet
        assert not manager.all_ready()
        for name in MODEL_REPOS:
            assert not manager.is_model_ready(name)


def test_model_manager_detects_ready_model() -> None:
    """is_model_ready returns True when config.json and weights exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ModelManager()
        model_dir = Path(tmpdir) / "paddleocr-vl-1.6"
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        (model_dir / "model.safetensors").write_text("weights", encoding="utf-8")

        # Patch the mapping for this test
        original_dir = manager.model_dir

        def patched_dir(name: str) -> Path:
            return model_dir if name == "paddleocr" else original_dir(name)

        manager.model_dir = patched_dir  # type: ignore[method-assign]

        assert manager.is_model_ready("paddleocr")
        assert not manager.is_model_ready("hunyuan")

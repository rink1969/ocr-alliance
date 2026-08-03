"""Tests for the FastAPI routes."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from src.main import create_app


def test_scan_directory_creates_tasks() -> None:
    """Scan endpoint should discover images and create pending tasks."""
    app = create_app()
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        input_dir.mkdir()

        # Create a nested image file
        nested = input_dir / "sub"
        nested.mkdir()
        Image.new("RGB", (100, 50), color="white").save(nested / "doc.png")

        resp = client.post(
            "/api/scan",
            json={
                "input_dir": str(input_dir),
                "output_dir": str(output_dir),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["added"] == 1

        # Listing tasks should return the image with its original extension
        list_resp = client.get(
            "/api/tasks",
            params={
                "input_dir": str(input_dir.resolve()),
                "output_dir": str(output_dir.resolve()),
            },
        )
        assert list_resp.status_code == 200
        tasks = list_resp.json()["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["relative_path"] == "sub/doc.png"


def test_models_status_endpoint() -> None:
    """Models status endpoint should list all built-in OCR models."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "all_ready" in data
    assert len(data["models"]) == 3
    names = {m["name"] for m in data["models"]}
    assert names == {"paddleocr", "hunyuan", "glm"}

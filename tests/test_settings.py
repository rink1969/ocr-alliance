"""Tests for settings management and LLM settings endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.config import settings
from src.core.settings_manager import mask_api_key, read_env, update_env
from src.main import create_app


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    """Save and restore global settings around each test."""
    saved = {
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "llm_api_key": settings.llm_api_key,
        "llm_temperature": settings.llm_temperature,
        "llm_max_tokens": settings.llm_max_tokens,
    }
    yield
    for key, value in saved.items():
        setattr(settings, key, value)


def test_mask_api_key() -> None:
    assert mask_api_key("") == ""
    assert mask_api_key("abc") == "****"
    assert mask_api_key("abcdefgh") == "****"
    assert mask_api_key("sk-1234567890abcd") == "sk-1...abcd"


def test_read_env_missing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    assert read_env() == {}


def test_update_env_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    update_env({"LLM_MODEL": "gpt-4o-mini", "LLM_TEMPERATURE": "0.5"})
    env = read_env()
    assert env["LLM_MODEL"] == "gpt-4o-mini"
    assert env["LLM_TEMPERATURE"] == "0.5"


def test_settings_reload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    original_model = settings.llm_model
    update_env({"LLM_MODEL": "reload-test-model"})
    settings.reload()
    try:
        assert settings.llm_model == "reload-test-model"
    finally:
        update_env({"LLM_MODEL": original_model})
        settings.reload()


def test_get_llm_settings_masks_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    update_env({"LLM_API_KEY": "sk-secret-key-1234"})
    settings.reload()
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/settings/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_api_key"] == "sk-s...1234"


def test_update_llm_settings_preserves_empty_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    update_env({"LLM_API_KEY": "sk-existing"})
    settings.reload()

    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/settings/llm",
        json={
            "llm_base_url": "https://example.com/v1",
            "llm_model": "model-x",
            "llm_api_key": "",
            "llm_temperature": 0.7,
            "llm_max_tokens": 4096,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_api_key"] == "sk-e...ting"
    assert settings.llm_api_key == "sk-existing"


def test_update_llm_settings_changes_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_root", tmp_path)
    update_env({"LLM_API_KEY": "sk-old"})
    settings.reload()

    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/settings/llm",
        json={
            "llm_base_url": "https://api.openai.com/v1",
            "llm_model": "gpt-4o",
            "llm_api_key": "sk-new-key-1234",
            "llm_temperature": 0.0,
            "llm_max_tokens": 8192,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_api_key"] == "sk-n...1234"
    assert settings.llm_api_key == "sk-new-key-1234"


def test_test_llm_connection_endpoint(monkeypatch) -> None:
    from src.api import routes

    def fake_test(base_url, model, api_key, timeout=30.0):
        return True, f"ok {base_url} {model}"

    monkeypatch.setattr(routes, "test_llm_connection", fake_test)

    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/settings/test-llm",
        json={"llm_base_url": "https://x.com", "llm_model": "m"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "ok https://x.com m" in data["message"]

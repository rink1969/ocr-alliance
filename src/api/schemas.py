"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    input_dir: str = Field(..., description="Absolute path to input directory")
    output_dir: str = Field(..., description="Absolute path to output directory")


class ScanResult(BaseModel):
    total: int
    added: int
    input_dir: str
    output_dir: str


class TaskItem(BaseModel):
    id: int | None
    input_path: str
    output_dir: str
    relative_path: str
    status: str
    results_json: dict
    error: str


class TaskListResponse(BaseModel):
    tasks: list[TaskItem]
    total: int
    pending: int
    processing: int
    done: int
    failed: int


class StartRequest(BaseModel):
    input_dir: str
    output_dir: str


class StartResponse(BaseModel):
    started: bool
    message: str


class StatusResponse(BaseModel):
    status: str
    progress: dict


class ModelStatusItem(BaseModel):
    name: str
    status: str
    message: str
    downloaded_bytes: int
    total_bytes: int | None


class ModelsStatusResponse(BaseModel):
    models: list[ModelStatusItem]
    all_ready: bool


class ModelDownloadRequest(BaseModel):
    model: str | None = Field(
        default=None,
        description="Model name to download, or null to download all missing",
    )


class ModelDownloadResponse(BaseModel):
    started: bool
    message: str


class LLMSettingsResponse(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_api_key: str = Field(
        ..., description="Masked API key (e.g. sk-...abcd) or empty string"
    )
    llm_temperature: float
    llm_max_tokens: int


class LLMSettingsUpdateRequest(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_api_key: str = Field(
        default="",
        description="New API key. Empty string means keep the existing key.",
    )
    llm_temperature: float
    llm_max_tokens: int


class LLMTestRequest(BaseModel):
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


class LLMTestResponse(BaseModel):
    success: bool
    message: str

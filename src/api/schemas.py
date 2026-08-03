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

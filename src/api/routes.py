"""FastAPI routes for OCR Alliance backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from src.api.schemas import (
    ScanRequest,
    ScanResult,
    StartRequest,
    StartResponse,
    StatusResponse,
    TaskItem,
    TaskListResponse,
)
from src.core.config import settings
from src.core.database import Task, TaskStatus, db
from src.core.file_utils import ensure_output_dirs, relative_path, scan_images
from src.core.scheduler import ProcessingState, scheduler

router = APIRouter()


@router.post("/scan", response_model=ScanResult)
async def scan(request: ScanRequest) -> ScanResult:
    """Scan input directory and create pending tasks."""
    input_path = Path(request.input_dir)
    output_path = Path(request.output_dir)

    if not input_path.is_dir():
        raise HTTPException(status_code=400, detail="Input directory does not exist")

    output_path.mkdir(parents=True, exist_ok=True)

    images = scan_images(input_path)
    ensure_output_dirs(input_path, output_path, images)

    added = 0
    for img in images:
        rel = relative_path(input_path, img)
        task = db.upsert_task(
            input_path=str(input_path.resolve()),
            output_dir=str(output_path.resolve()),
            relative_path=rel,
        )
        if task and task.status == TaskStatus.PENDING:
            added += 1

    return ScanResult(
        total=len(images),
        added=added,
        input_dir=str(input_path.resolve()),
        output_dir=str(output_path.resolve()),
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    input_dir: str | None = None,
    output_dir: str | None = None,
) -> TaskListResponse:
    """List tasks, optionally filtered by input/output directory."""
    tasks = db.list_tasks(input_path=input_dir, output_dir=output_dir)

    def _to_item(task: Task) -> dict:
        return task.to_dict()

    counts = {"pending": 0, "processing": 0, "done": 0, "failed": 0}
    for task in tasks:
        counts[task.status.value] += 1

    return TaskListResponse(
        tasks=[TaskItem(**_to_item(t)) for t in tasks],
        total=len(tasks),
        **counts,
    )


@router.post("/start", response_model=StartResponse)
async def start(request: StartRequest) -> StartResponse:
    """Start processing pending tasks for a job."""
    input_path = Path(request.input_dir)
    output_path = Path(request.output_dir)

    if not input_path.is_dir() or not output_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid input or output directory")

    if scheduler.state == ProcessingState.RUNNING:
        return StartResponse(started=False, message="Scheduler is already running")

    scheduler.start(str(input_path.resolve()), str(output_path.resolve()))
    return StartResponse(started=True, message="Processing started")


@router.post("/stop", response_model=StartResponse)
async def stop() -> StartResponse:
    """Stop the processing scheduler."""
    was_running = scheduler.state == ProcessingState.RUNNING
    scheduler.stop()
    return StartResponse(
        started=False,
        message="Processing stopped" if was_running else "Scheduler was not running",
    )


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Get current scheduler status and progress."""
    tasks = db.list_tasks(
        input_path=scheduler.input_dir,
        output_dir=scheduler.output_dir,
    )
    counts = {"pending": 0, "processing": 0, "done": 0, "failed": 0}
    for task in tasks:
        counts[task.status.value] += 1

    return StatusResponse(
        status=scheduler.state.value,
        progress={
            "total": len(tasks),
            **counts,
            "current_file": scheduler.current_file,
        },
    )


@router.get("/image")
async def get_image(path: str) -> Response:
    """Serve an image file from the local filesystem for preview."""
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(file_path))


@router.get("/settings")
async def get_settings() -> dict:
    """Return current settings safe to expose to UI."""
    return {
        "models_dir": str(settings.models_dir),
        "output_suffixes": settings.output_suffixes,
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
    }

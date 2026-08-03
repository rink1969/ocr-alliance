"""SQLite database layer for task queue and progress persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.config import settings


class TaskStatus(str, Enum):
    """Possible statuses for an OCR task."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    """A single OCR task row."""

    id: int | None
    input_path: str
    output_dir: str
    relative_path: str
    status: TaskStatus
    results_json: dict[str, Any]
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "input_path": self.input_path,
            "output_dir": self.output_dir,
            "relative_path": self.relative_path,
            "status": self.status.value,
            "results_json": self.results_json,
            "error": self.error,
        }


class Database:
    """Simple SQLite wrapper for OCR task queue."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_path TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    results_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(input_path, output_dir, relative_path)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
                """
            )
            conn.commit()

    def upsert_task(self, input_path: str, output_dir: str, relative_path: str) -> Task:
        """Insert or ignore a task row."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO tasks
                (input_path, output_dir, relative_path, status, results_json, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    input_path,
                    output_dir,
                    relative_path,
                    TaskStatus.PENDING.value,
                    "{}",
                    "",
                ),
            )
            conn.commit()
            return self.get_task(input_path, output_dir, relative_path)

    def get_task(
        self, input_path: str, output_dir: str, relative_path: str
    ) -> Task | None:
        """Fetch a single task by composite key."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE input_path = ? AND output_dir = ? AND relative_path = ?
                """,
                (input_path, output_dir, relative_path),
            ).fetchone()
            return self._row_to_task(row) if row else None

    def list_tasks(
        self,
        input_path: str | None = None,
        output_dir: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list[Any] = []
        if input_path:
            query += " AND input_path = ?"
            params.append(input_path)
        if output_dir:
            query += " AND output_dir = ?"
            params.append(output_dir)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY relative_path"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task(row) for row in rows]

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        results_json: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        """Update task status and optional results/error."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, results_json = ?, error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    status.value,
                    json.dumps(results_json or {}, ensure_ascii=False),
                    error,
                    task_id,
                ),
            )
            conn.commit()

    def reset_incomplete(self, input_path: str, output_dir: str) -> None:
        """Reset processing/pending tasks for a job to pending."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, error = '', updated_at = CURRENT_TIMESTAMP
                WHERE input_path = ? AND output_dir = ? AND status IN (?, ?)
                """,
                (
                    TaskStatus.PENDING.value,
                    input_path,
                    output_dir,
                    TaskStatus.PROCESSING.value,
                    TaskStatus.PENDING.value,
                ),
            )
            conn.commit()

    def delete_job(self, input_path: str, output_dir: str) -> None:
        """Remove all tasks for a given input/output pair."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE input_path = ? AND output_dir = ?",
                (input_path, output_dir),
            )
            conn.commit()

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            input_path=row["input_path"],
            output_dir=row["output_dir"],
            relative_path=row["relative_path"],
            status=TaskStatus(row["status"]),
            results_json=json.loads(row["results_json"]),
            error=row["error"],
        )


# Global DB instance
db = Database()

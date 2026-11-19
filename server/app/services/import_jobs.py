"""
In-process registry and runner for background CSV imports.

The upload endpoint validates the file header, registers a job and returns a
job id immediately.  FastAPI's BackgroundTasks then runs :func:`run_import_job`
in the thread pool while the client polls ``GET /api/imports/jobs/{job_id}``.

Progress is stored in memory rather than in SQLite so the import itself can
stay in one transaction: polling can read the progress without committing
half-written student rows.  Jobs are bounded and evicted from memory once
finished; this backend runs as a single process, which is the deployment the
assignment describes.  A multi-worker deployment would move this registry to
Redis or a database table.
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from app.config.db import SessionLocal
from app.importer.pipeline import process_file
from app.models.imports import Import as ImportModel
from app.schemas.imports import ImportSummarySchema
from app.services.import_service import persist_import

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "processing", "completed", "failed"]
JobStage = Literal["queued", "validating", "saving", "completed", "failed"]

MAX_JOBS = 100
_VALIDATION_START = 5
_VALIDATION_END = 60
_SAVING_START = 62
_SAVING_END = 95


@dataclass
class ImportJobState:
    job_id: str
    filename: str
    size_bytes: int
    status: JobStatus = "queued"
    stage: JobStage = "queued"
    progress: int = 0
    processed_rows: int = 0
    total_rows: Optional[int] = None
    summary: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "processed_rows": self.processed_rows,
            "total_rows": self.total_rows,
            "summary": self.summary,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


_jobs: "OrderedDict[str, ImportJobState]" = OrderedDict()
_lock = threading.Lock()


def _evict_locked() -> None:
    """Drop the oldest finished jobs once the registry is full."""
    while len(_jobs) > MAX_JOBS:
        for job_id, state in list(_jobs.items()):
            if state.status in ("completed", "failed"):
                del _jobs[job_id]
                break
        else:
            break


def create_job(filename: str, size_bytes: int) -> dict:
    job_id = uuid.uuid4().hex
    state = ImportJobState(job_id=job_id, filename=filename, size_bytes=size_bytes)
    with _lock:
        _jobs[job_id] = state
        _evict_locked()
    return state.to_dict()


def get_job(job_id: str) -> Optional[dict]:
    with _lock:
        state = _jobs.get(job_id)
        return state.to_dict() if state is not None else None


def _update(job_id: str, **fields) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        for key, value in fields.items():
            setattr(state, key, value)
        state.updated_at = datetime.utcnow()


def _set_progress(
    job_id: str,
    *,
    processed_rows: Optional[int] = None,
    total_rows: Optional[int] = None,
    progress: int,
    stage: JobStage,
) -> None:
    """Update progress monotonically; a late callback must not move it back."""
    with _lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        state.status = "processing"
        state.stage = stage
        if processed_rows is not None:
            state.processed_rows = processed_rows
        if total_rows is not None:
            state.total_rows = total_rows
        state.progress = max(state.progress, min(progress, 99))
        state.updated_at = datetime.utcnow()


def mark_completed(job_id: str, summary: dict) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        state.status = "completed"
        state.stage = "completed"
        state.progress = 100
        state.summary = summary
        state.error = None
        state.updated_at = datetime.utcnow()


def mark_failed(job_id: str, message: str) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        state.status = "failed"
        state.stage = "failed"
        state.error = message
        state.updated_at = datetime.utcnow()


def run_import_job(job_id: str, raw_bytes: bytes, filename: str) -> None:
    """Validate and persist an upload without blocking the HTTP response."""
    _set_progress(
        job_id,
        processed_rows=0,
        progress=2,
        stage="validating",
    )

    db = SessionLocal()

    def validation_progress(rows_seen: int, estimated_total: int) -> None:
        if estimated_total > 0:
            fraction = min(rows_seen / estimated_total, 1)
            progress = _VALIDATION_START + int(
                (_VALIDATION_END - _VALIDATION_START) * fraction
            )
        else:
            progress = _VALIDATION_START
        _set_progress(
            job_id,
            processed_rows=rows_seen,
            total_rows=estimated_total or None,
            progress=progress,
            stage="validating",
        )

    def saving_progress(rows_saved: int, total: int) -> None:
        fraction = (rows_saved / total) if total else 1
        progress = _SAVING_START + int((_SAVING_END - _SAVING_START) * fraction)
        # processed_rows stays at the validated row count; only the bar moves
        # during the write phase, so the displayed row count never goes back.
        _set_progress(job_id, progress=progress, stage="saving")

    try:
        result = process_file(
            raw_bytes,
            filename,
            on_progress=validation_progress,
        )

        # Validation is complete, so the exact row count is known.
        _set_progress(
            job_id,
            processed_rows=result.rows_read,
            total_rows=result.rows_read,
            progress=_VALIDATION_END,
            stage="saving",
        )

        import_record = persist_import(
            db,
            raw_bytes,
            filename,
            result,
            on_progress=saving_progress,
        )

        summary = ImportSummarySchema.model_validate(import_record).model_dump(mode="json")
        mark_completed(job_id, summary)
    except ValueError as exc:
        # Expected file-level failure discovered after the upload was accepted.
        db.rollback()
        logger.warning("Import job %s rejected: %s", job_id, exc)
        mark_failed(job_id, str(exc))
    except Exception:
        db.rollback()
        logger.exception("Import job %s failed unexpectedly", job_id)
        mark_failed(
            job_id,
            "The import failed while saving. No student records were changed. "
            "Please try again.",
        )
    finally:
        db.close()

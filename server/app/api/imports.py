"""
Import endpoints.

POST  /api/imports                 — accept a CSV and queue background processing
GET   /api/imports/jobs/{job_id}   — poll background import status/progress
GET   /api/imports/{id}            — summary of a completed import
GET   /api/imports/{id}/errors     — paginated row errors
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_db
from app.core import ApiResponse, NotFoundError, UnprocessableFileError
from app.importer.decode import decode_file
from app.importer.parser import parse_csv
from app.models.imports import Import, ImportError as ImportErrorModel
from app.schemas.imports import ImportErrorSchema, ImportJobSchema, ImportSummarySchema
from app.services.import_jobs import create_job, get_job, run_import_job

router = APIRouter(prefix="/imports", tags=["imports"])


def _validate_upload_header(raw_bytes: bytes, filename: str) -> None:
    """Fail fast on bad files before accepting a background job.

    Only the header and the presence of at least one data row are checked
    here; full row validation happens in the background.
    """
    text, _ = decode_file(raw_bytes, filename)
    _header, row_iter = parse_csv(text)
    try:
        next(row_iter)
    except StopIteration:
        raise ValueError("The file contains only a header row and no student data.")


@router.post("", status_code=202)
def upload_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept a CSV and process it asynchronously.

    Returns 202 with a job id.  Poll ``GET /api/imports/jobs/{job_id}`` until
    ``status`` is ``completed`` or ``failed``.  File-level problems are still
    rejected immediately with 422.
    """
    raw_bytes = file.file.read()
    filename = file.filename or "upload.csv"

    try:
        _validate_upload_header(raw_bytes, filename)
    except ValueError as exc:
        raise UnprocessableFileError(str(exc))

    job = create_job(filename, len(raw_bytes))
    background_tasks.add_task(run_import_job, job["job_id"], raw_bytes, filename)

    return ApiResponse.accepted(
        ImportJobSchema.model_validate(job).model_dump(mode="json"),
        message="Upload accepted. The import is running in the background.",
    )


@router.get("/jobs/{job_id}")
def get_import_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise NotFoundError(
            f"Import job '{job_id}' was not found. It may have expired; upload the file again."
        )
    return ApiResponse.ok(ImportJobSchema.model_validate(job).model_dump(mode="json"))


@router.get("/{import_id}")
def get_import(import_id: int, db: Session = Depends(get_db)):
    record = db.query(Import).filter(Import.id == import_id).first()
    if record is None:
        raise NotFoundError(f"Import {import_id} not found.")
    return ApiResponse.ok(
        ImportSummarySchema.model_validate(record).model_dump(mode="json")
    )


@router.get("/{import_id}/errors")
def get_import_errors(
    import_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not db.query(Import).filter(Import.id == import_id).first():
        raise NotFoundError(f"Import {import_id} not found.")

    total = (
        db.query(ImportErrorModel)
        .filter(ImportErrorModel.import_id == import_id)
        .count()
    )
    errors = (
        db.query(ImportErrorModel)
        .filter(ImportErrorModel.import_id == import_id)
        .order_by(ImportErrorModel.row_number.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        ImportErrorSchema.model_validate(e).model_dump(mode="json")
        for e in errors
    ]
    return ApiResponse.paginated(items, total=total, page=page, page_size=page_size)

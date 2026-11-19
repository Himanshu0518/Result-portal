"""
Import endpoints.

POST  /api/imports                — upload CSV
GET   /api/imports/{id}           — summary of one import
GET   /api/imports/{id}/errors    — paginated row errors
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_db
from app.core import ApiResponse, NotFoundError, UnprocessableFileError
from app.importer.pipeline import process_file
from app.models.imports import Import, ImportError as ImportErrorModel
from app.schemas.imports import ImportErrorSchema, ImportSummarySchema
from app.services.import_service import persist_import

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", status_code=201)
def upload_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a CSV file.

    Returns 201 with summary + first 50 errors on success.
    Returns 422 for file-level failures (bad format, missing columns, etc.).
    Returns 201 even when individual rows are rejected — that is not a failure.
    """
    raw_bytes = file.file.read()
    filename = file.filename or "upload.csv"

    try:
        pipeline_result = process_file(raw_bytes, filename)
    except ValueError as exc:
        raise UnprocessableFileError(str(exc))

    import_record = persist_import(db, raw_bytes, filename, pipeline_result)

    first_errors = (
        db.query(ImportErrorModel)
        .filter(ImportErrorModel.import_id == import_record.id)
        .order_by(ImportErrorModel.row_number.asc())
        .limit(50)
        .all()
    )

    # mode="json" makes Pydantic serialise datetime/date to ISO strings
    # so JSONResponse (stdlib json) can handle them without a custom encoder.
    data = {
        "summary": ImportSummarySchema.model_validate(import_record).model_dump(mode="json"),
        "first_errors": [
            ImportErrorSchema.model_validate(e).model_dump(mode="json")
            for e in first_errors
        ],
    }
    return ApiResponse.created(data, message="File imported successfully.")


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

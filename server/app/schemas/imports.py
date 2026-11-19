from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ImportErrorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_id: int
    row_number: int
    student_id: Optional[str] = None
    field: Optional[str] = None
    code: str
    message: str


class ImportSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_sha256: str
    size_bytes: int
    rows_read: int
    new_count: int
    updated_count: int
    unchanged_count: int
    rejected_count: int
    problem_count: int
    encoding_note: Optional[str] = None
    created_at: datetime


class ImportCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: ImportSummarySchema
    first_errors: list[ImportErrorSchema]

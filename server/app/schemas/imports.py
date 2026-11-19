from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ImportErrorSchema(BaseModel):
    id: int
    import_id: int
    row_number: int
    student_id: Optional[str]
    field: Optional[str]
    code: str
    message: str

    class Config:
        from_attributes = True


class ImportSummarySchema(BaseModel):
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
    encoding_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ImportCreateResponse(BaseModel):
    summary: ImportSummarySchema
    first_errors: list[ImportErrorSchema]

    class Config:
        from_attributes = True

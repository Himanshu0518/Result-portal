from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StudentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    full_name: str
    email: str
    grade_level: int
    section: str
    total: float
    percentage: float
    grade: str
    pass_fail: str


class StudentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    full_name: str
    email: str
    date_of_birth: date
    grade_level: int
    section: str
    maths: float
    science: float
    english: float
    social_studies: float
    second_language: float
    last_import_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # Computed fields (not stored in DB; injected by student_service)
    total: float
    percentage: float
    grade: str
    pass_fail: str

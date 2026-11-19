from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class StudentListItem(BaseModel):
    student_id: str
    full_name: str
    email: str
    grade_level: int
    section: str
    total: float
    percentage: float
    grade: str
    pass_fail: str

    class Config:
        from_attributes = True


class StudentDetail(BaseModel):
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
    last_import_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    # Computed
    total: float
    percentage: float
    grade: str
    pass_fail: str

    class Config:
        from_attributes = True

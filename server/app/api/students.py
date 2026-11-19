"""
Student endpoints.

GET /api/students                — list + search + paginate
GET /api/students/{student_id}   — full report with computed grade
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_db
from app.core import ApiResponse, NotFoundError
from app.schemas.students import StudentDetail, StudentListItem
from app.services.student_service import get_student, list_students

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
def search_students(
    q: Optional[str] = Query(None, description="Search by name (contains) or student ID (contains)"),
    grade_level: Optional[int] = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_students(
        db, q=q, grade_level=grade_level, page=page, page_size=page_size
    )
    # items are dicts from student_service with computed grade fields already injected.
    # Validate through schema so we get consistent field ordering and type coercion,
    # then dump with mode="json" to serialise date/datetime to ISO strings.
    serialised = [
        StudentListItem.model_validate(item).model_dump(mode="json")
        for item in items
    ]
    return ApiResponse.paginated(serialised, total=total, page=page, page_size=page_size)


@router.get("/{student_id}")
def get_student_report(student_id: str, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if student is None:
        raise NotFoundError(f"Student '{student_id.upper()}' not found.")
    return ApiResponse.ok(
        StudentDetail.model_validate(student).model_dump(mode="json")
    )

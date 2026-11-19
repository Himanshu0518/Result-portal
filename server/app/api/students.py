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
from app.services.student_service import list_students, get_student

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
def search_students(
    q: Optional[str] = Query(None),
    grade_level: Optional[int] = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_students(db, q=q, grade_level=grade_level, page=page, page_size=page_size)
    # Serialise dates/datetimes to strings for JSON.
    serialised = []
    for item in items:
        d = dict(item)
        for k, v in d.items():
            if hasattr(v, 'isoformat'):
                d[k] = v.isoformat()
        serialised.append(d)
    return ApiResponse.paginated(serialised, total=total, page=page, page_size=page_size)


@router.get("/{student_id}")
def get_student_report(student_id: str, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if student is None:
        raise NotFoundError(f"Student '{student_id.upper()}' not found.")
    # Serialise dates/datetimes.
    d = dict(student)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
    return ApiResponse.ok(d)

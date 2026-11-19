"""
DB query layer for students.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.students import Student
from app.grading import compute_grade


def _with_grade(s: Student) -> dict:
    g = compute_grade(
        s.maths, s.science, s.english, s.social_studies, s.second_language
    )
    return {
        "student_id": s.student_id,
        "full_name": s.full_name,
        "email": s.email,
        "date_of_birth": s.date_of_birth,
        "grade_level": s.grade_level,
        "section": s.section,
        "maths": s.maths,
        "science": s.science,
        "english": s.english,
        "social_studies": s.social_studies,
        "second_language": s.second_language,
        "last_import_id": s.last_import_id,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        **g,
    }


def list_students(
    db: Session,
    q: Optional[str] = None,
    grade_level: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    Returns (items, total_count).
    items are dicts with computed grade fields.
    """
    page_size = min(page_size, 100)
    page = max(page, 1)

    query = db.query(Student)

    if q:
        # Escape LIKE special chars.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query = query.filter(
            func.lower(Student.full_name).like(pattern.lower())
            | Student.student_id.like(pattern.upper())
        )

    if grade_level is not None:
        query = query.filter(Student.grade_level == grade_level)

    total = query.count()
    students = (
        query
        .order_by(Student.student_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [_with_grade(s) for s in students], total


def get_student(db: Session, student_id: str) -> Optional[dict]:
    """
    Returns full student dict with computed grade, or None if not found.
    student_id is normalised to upper-case before lookup.
    """
    s = db.query(Student).filter(
        Student.student_id == student_id.upper()
    ).first()
    if s is None:
        return None
    return _with_grade(s)

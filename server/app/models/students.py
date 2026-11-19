"""
Student model.

Derived values (total, percentage, grade, pass/fail) are NOT stored; they are
computed by grading.py on read so changing the grading scheme needs no migration.
parent_phone from the sample file is deliberately not stored (not required,
and it is personal data we do not need).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.db import Base


SUBJECTS = ("maths", "science", "english", "social_studies", "second_language")


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)  # always UPPER-CASE
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)  # always lower-case
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(1), nullable=False)  # A-F, upper-case

    maths: Mapped[float] = mapped_column(Float, nullable=False)
    science: Mapped[float] = mapped_column(Float, nullable=False)
    english: Mapped[float] = mapped_column(Float, nullable=False)
    social_studies: Mapped[float] = mapped_column(Float, nullable=False)
    second_language: Mapped[float] = mapped_column(Float, nullable=False)

    last_import_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("imports.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    # onupdate uses a Python-side callable so it works with SQLite (server_onupdate
    # would need a trigger; func.now() alone would only fire on the SQL side for
    # INSERT, not UPDATE).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        # Data-integrity guards: the importer validates first; these catch any
        # future bug or manual edit that slips through.
        CheckConstraint("length(student_id) BETWEEN 3 AND 20", name="ck_students_id_len"),
        CheckConstraint("student_id = upper(student_id)", name="ck_students_id_upper"),
        CheckConstraint("length(full_name) BETWEEN 2 AND 100", name="ck_students_name_len"),
        CheckConstraint("email = lower(email)", name="ck_students_email_lower"),
        CheckConstraint("grade_level BETWEEN 1 AND 12", name="ck_students_grade_level"),
        CheckConstraint("section IN ('A','B','C','D','E','F')", name="ck_students_section"),
        *(
            CheckConstraint(f"{s} BETWEEN 0 AND 100", name=f"ck_students_{s}_range")
            for s in SUBJECTS
        ),
        # Functional index on lower(full_name) for case-insensitive name search.
        # Standard Index("...", "full_name") would only help case-sensitive lookups.
        Index("ix_students_full_name_lower", text("lower(full_name)")),
        Index("ix_students_grade_level", "grade_level"),
    )

    def __repr__(self) -> str:
        return f"<Student id={self.student_id!r} name={self.full_name!r}>"

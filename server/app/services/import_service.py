"""
DB write layer for imports.

Handles:
- sha256 duplicate detection (same file re-uploaded).
- Upsert students in one transaction.
- Persist Import record + all ImportError records.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.imports import Import, ImportError as ImportErrorModel
from app.models.students import Student
from app.importer.pipeline import PipelineResult


def _sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def persist_import(
    db: Session,
    raw_bytes: bytes,
    filename: str,
    pipeline_result: PipelineResult,
) -> Import:
    """
    Persist the import summary and all errors.
    Upserts valid student rows.
    If this exact file was uploaded before (same sha256), returns the previous
    import record with counts zeroed to new=0, updated=0, unchanged=N.

    Raises on DB error (transaction rolled back by caller's context manager).
    """
    file_sha256 = _sha256(raw_bytes)
    size_bytes = len(raw_bytes)

    # --- Check for re-upload (same sha256) ---
    existing = (
        db.query(Import)
        .filter(Import.file_sha256 == file_sha256)
        .first()
    )
    if existing is not None:
        # Idempotent re-upload: return a synthetic summary.
        # We don't re-write the DB; just describe what's already there.
        unchanged = len(pipeline_result.valid_rows)
        import_record = Import(
            filename=filename,
            file_sha256=file_sha256,
            size_bytes=size_bytes,
            rows_read=pipeline_result.rows_read,
            new_count=0,
            updated_count=0,
            unchanged_count=unchanged,
            rejected_count=len(set(e.row_number for e in pipeline_result.errors)),
            problem_count=len(pipeline_result.errors),
            encoding_note=pipeline_result.encoding_note,
        )
        db.add(import_record)
        db.flush()
        # Persist errors for this re-upload record too.
        for err in pipeline_result.errors:
            db.add(ImportErrorModel(
                import_id=import_record.id,
                row_number=err.row_number,
                student_id=err.student_id,
                field=err.field,
                code=err.code,
                message=err.message,
            ))
        db.commit()
        return import_record

    # --- New import ---
    # Determine new vs updated vs unchanged.
    new_count = 0
    updated_count = 0
    unchanged_count = 0

    # Fetch existing student IDs in one query.
    valid_ids = [r.student_id for r in pipeline_result.valid_rows]
    if valid_ids:
        existing_ids = set(
            row[0]
            for row in db.query(Student.student_id)
            .filter(Student.student_id.in_(valid_ids))
            .all()
        )
    else:
        existing_ids = set()

    # Build a dict of current DB rows to detect unchanged.
    existing_students: dict[str, Student] = {}
    if existing_ids:
        for s in (
            db.query(Student)
            .filter(Student.student_id.in_(list(existing_ids)))
            .all()
        ):
            existing_students[s.student_id] = s

    # Create the import record first to get its ID.
    rejected_count = len(set(e.row_number for e in pipeline_result.errors))
    import_record = Import(
        filename=filename,
        file_sha256=file_sha256,
        size_bytes=size_bytes,
        rows_read=pipeline_result.rows_read,
        new_count=0,  # will update after upsert
        updated_count=0,
        unchanged_count=0,
        rejected_count=rejected_count,
        problem_count=len(pipeline_result.errors),
        encoding_note=pipeline_result.encoding_note,
    )
    db.add(import_record)
    db.flush()  # get import_record.id

    now = datetime.utcnow()

    # Upsert students.
    for row in pipeline_result.valid_rows:
        sid = row.student_id
        if sid in existing_students:
            existing_s = existing_students[sid]
            # Check if anything actually changed.
            changed = (
                existing_s.full_name != row.full_name
                or existing_s.email != row.email
                or existing_s.date_of_birth != row.date_of_birth
                or existing_s.grade_level != row.grade_level
                or existing_s.section != row.section
                or existing_s.maths != row.maths
                or existing_s.science != row.science
                or existing_s.english != row.english
                or existing_s.social_studies != row.social_studies
                or existing_s.second_language != row.second_language
            )
            if changed:
                existing_s.full_name = row.full_name
                existing_s.email = row.email
                existing_s.date_of_birth = row.date_of_birth
                existing_s.grade_level = row.grade_level
                existing_s.section = row.section
                existing_s.maths = row.maths
                existing_s.science = row.science
                existing_s.english = row.english
                existing_s.social_studies = row.social_studies
                existing_s.second_language = row.second_language
                existing_s.last_import_id = import_record.id
                existing_s.updated_at = now
                updated_count += 1
            else:
                unchanged_count += 1
        else:
            db.add(Student(
                student_id=sid,
                full_name=row.full_name,
                email=row.email,
                date_of_birth=row.date_of_birth,
                grade_level=row.grade_level,
                section=row.section,
                maths=row.maths,
                science=row.science,
                english=row.english,
                social_studies=row.social_studies,
                second_language=row.second_language,
                last_import_id=import_record.id,
            ))
            new_count += 1

    # Update counts.
    import_record.new_count = new_count
    import_record.updated_count = updated_count
    import_record.unchanged_count = unchanged_count

    # Persist errors.
    for err in pipeline_result.errors:
        db.add(ImportErrorModel(
            import_id=import_record.id,
            row_number=err.row_number,
            student_id=err.student_id,
            field=err.field,
            code=err.code,
            message=err.message,
        ))

    db.commit()
    return import_record

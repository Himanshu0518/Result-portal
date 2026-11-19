"""
Import pipeline.

Orchestrates: decode -> parse -> validate -> dedupe
Returns a PipelineResult object.

This module has NO database or FastAPI imports — it is a pure function.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from .decode import decode_file
from .parser import count_data_rows, parse_csv, REQUIRED_COLUMNS
from .validators import (
    validate_student_id,
    validate_full_name,
    validate_email,
    validate_date_of_birth,
    validate_grade_level,
    validate_section,
    validate_mark,
)


@dataclass
class RowError:
    row_number: int
    student_id: Optional[str]
    field: Optional[str]
    code: str
    message: str


@dataclass
class ValidRow:
    row_number: int
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


@dataclass
class PipelineResult:
    valid_rows: list[ValidRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    rows_read: int = 0
    encoding_note: Optional[str] = None


SUBJECT_FIELDS = ["maths", "science", "english", "social_studies", "second_language"]

# Called with (rows_processed_so_far, estimated_total_rows).
ProgressCallback = Callable[[int, int], None]


def process_file(
    raw_bytes: bytes,
    filename: str,
    today: Optional[date] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> PipelineResult:
    """
    Full pipeline: decode -> parse -> validate -> dedupe.

    Raises ValueError for file-level errors (caller maps these to HTTP 422).
    Never raises for row-level errors; they go into PipelineResult.errors.
    """
    # 1. Decode.
    text, encoding_note = decode_file(raw_bytes, filename)

    # 2. Parse header + get row iterator.
    _header, row_iter = parse_csv(text)

    # Progress is estimated from a cheap pre-count; the exact total is only
    # known after validation.  Counting is skipped when nobody is listening.
    estimated_rows = count_data_rows(text) if on_progress is not None else 0
    if on_progress is not None:
        on_progress(0, estimated_rows)

    result = PipelineResult(encoding_note=encoding_note)

    # Tracks which student_ids have been claimed in this file.
    # Key: upper-cased ID. Value: row_number_of_first_claim.
    claimed_ids: dict[str, int] = {}

    had_any_data_row = False

    for row_number, raw_fields, col_index, num_expected in row_iter:
        had_any_data_row = True
        result.rows_read += 1

        # --- Wrong field count ---
        if len(raw_fields) != num_expected:
            result.errors.append(RowError(
                row_number=row_number,
                student_id=None,
                field=None,
                code="WRONG_FIELD_COUNT",
                message=(
                    f"Row has {len(raw_fields)} field(s) but the header has "
                    f"{num_expected}. Expected {num_expected} fields."
                ),
            ))
            continue

        # Extract raw values by column index.
        def get(col: str) -> str:
            return raw_fields[col_index[col]]

        raw_id = get("student_id").strip().upper()

        # --- Duplicate ID check (before validation, first row claims the ID) ---
        if raw_id:
            if raw_id in claimed_ids:
                result.errors.append(RowError(
                    row_number=row_number,
                    student_id=raw_id,
                    field="student_id",
                    code="DUPLICATE_ID",
                    message=(
                        f"Student ID '{raw_id}' already appears at line "
                        f"{claimed_ids[raw_id]} in this file."
                    ),
                ))
                continue
            # Claim the ID regardless of whether this row will pass validation.
            claimed_ids[raw_id] = row_number

        # --- Per-field validation ---
        row_errors: list[RowError] = []

        norm_id, err = validate_student_id(get("student_id"))
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        norm_name, err = validate_full_name(get("full_name"))
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        norm_email, err = validate_email(get("email"))
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        norm_dob, err = validate_date_of_birth(get("date_of_birth"), today=today)
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        norm_grade, err = validate_grade_level(get("grade_level"))
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        norm_section, err = validate_section(get("section"))
        if err:
            row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))

        subject_values: dict[str, float] = {}
        for subj in SUBJECT_FIELDS:
            norm_mark, err = validate_mark(get(subj), subj)
            if err:
                row_errors.append(RowError(row_number=row_number, student_id=raw_id or None, field=err[0], code=err[1], message=err[2]))
            else:
                subject_values[subj] = norm_mark

        if row_errors:
            result.errors.extend(row_errors)
            continue

        result.valid_rows.append(ValidRow(
            row_number=row_number,
            student_id=norm_id,
            full_name=norm_name,
            email=norm_email,
            date_of_birth=norm_dob,
            grade_level=norm_grade,
            section=norm_section,
            maths=subject_values["maths"],
            science=subject_values["science"],
            english=subject_values["english"],
            social_studies=subject_values["social_studies"],
            second_language=subject_values["second_language"],
        ))

        if on_progress is not None and result.rows_read % 250 == 0:
            on_progress(result.rows_read, estimated_rows)

    if not had_any_data_row:
        raise ValueError("The file contains only a header row and no student data.")

    if on_progress is not None:
        on_progress(result.rows_read, result.rows_read)

    return result

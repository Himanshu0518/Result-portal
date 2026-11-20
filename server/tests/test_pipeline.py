"""
Tests for app.importer.pipeline.process_file.

Uses make_csv from conftest to build CSV bytes.
All file-level errors raise ValueError; row-level errors go into PipelineResult.errors.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.importer.pipeline import process_file, PipelineResult
from app.importer.decode import MAX_FILE_SIZE
from tests.conftest import make_csv, HEADER


# Fixed "today" so DOB range tests are deterministic.
TODAY = date(2026, 11, 20)

# A complete valid data row (all fields good, DOB gives age=16).
_GOOD = "STU-{n},Student{n} Name,stu{n}@example.com,2010-05-15,10,A,80,70,75,65,60"


def good_row(n: int) -> str:
    return _GOOD.format(n=n)


# ── 1. Valid file ──────────────────────────────────────────────────────────

def test_valid_file_three_rows():
    csv_bytes = make_csv(good_row(1), good_row(2), good_row(3))
    result = process_file(csv_bytes, "test.csv", today=TODAY)
    assert isinstance(result, PipelineResult)
    assert result.rows_read == 3
    assert len(result.valid_rows) == 3
    assert result.errors == []


# ── 2. Blank lines advance line number but are not counted in rows_read ───

def test_blank_line_advances_row_number():
    # Header = line 1, blank = line 2, data = line 3
    csv_bytes = (HEADER + "\n\n" + good_row(1)).encode("utf-8")
    result = process_file(csv_bytes, "test.csv", today=TODAY)
    assert result.rows_read == 1
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0].row_number == 3


# ── 3. DUPLICATE_ID: first row claims ID even if it has validation errors ─

def test_duplicate_id_first_bad_second_good():
    # Row 2: same ID, bad email → claims ID, gets INVALID_FORMAT
    # Row 3: same ID, good data → gets DUPLICATE_ID, NOT added to valid_rows
    row_bad_email = "STU-DUP,Bad Student,NOT_AN_EMAIL,2010-05-15,10,A,80,70,75,65,60"
    row_good = "STU-DUP,Good Student,good@example.com,2010-05-15,10,A,80,70,75,65,60"
    csv_bytes = make_csv(row_bad_email, row_good)
    result = process_file(csv_bytes, "test.csv", today=TODAY)

    assert len(result.valid_rows) == 0
    codes = [e.code for e in result.errors]
    assert "INVALID_FORMAT" in codes
    assert "DUPLICATE_ID" in codes

    dup_err = next(e for e in result.errors if e.code == "DUPLICATE_ID")
    assert dup_err.student_id == "STU-DUP"
    assert dup_err.row_number == 3


# ── 4. WRONG_FIELD_COUNT does not block ID claim ──────────────────────────

def test_wrong_field_count_does_not_block_id():
    # Row 2: too few fields — WRONG_FIELD_COUNT, ID not claimed (continue before claim)
    # Row 3: same ID with correct fields → should be valid
    row_short = "STU-WFC,Missing Fields"       # only 2 fields
    row_good = good_row(99).replace("STU-99", "STU-WFC")
    csv_bytes = make_csv(row_short, row_good)
    result = process_file(csv_bytes, "test.csv", today=TODAY)

    wfc_errors = [e for e in result.errors if e.code == "WRONG_FIELD_COUNT"]
    assert len(wfc_errors) == 1
    assert wfc_errors[0].row_number == 2

    # Row 3 should be valid — WRONG_FIELD_COUNT does not claim the ID
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0].student_id == "STU-WFC"


# ── 5. Multiple errors per row: counted once in rejected ──────────────────

def test_multiple_errors_one_rejected_row():
    # Blank name AND invalid email → 2 errors, 1 rejected row
    row_multi = "STU-M01,,NOT_AN_EMAIL,2010-05-15,10,A,80,70,75,65,60"
    csv_bytes = make_csv(row_multi)
    result = process_file(csv_bytes, "test.csv", today=TODAY)

    assert result.rows_read == 1
    assert len(result.valid_rows) == 0
    # At least 2 errors recorded (MISSING_REQUIRED for name + INVALID_FORMAT for email)
    assert len(result.errors) >= 2
    # But only 1 unique rejected row number
    assert len({e.row_number for e in result.errors}) == 1


# ── 6. All 5 error codes appear ───────────────────────────────────────────

def test_all_five_error_codes():
    # WRONG_FIELD_COUNT: too few fields
    row_wfc = "STU-WC1,Only Two Fields"
    # MISSING_REQUIRED: blank name
    row_missing = "STU-MR1,,mr1@example.com,2010-05-15,10,A,80,70,75,65,60"
    # INVALID_FORMAT: bad email
    row_invalid = "STU-IF1,IF One,BADEMAIL,2010-05-15,10,A,80,70,75,65,60"
    # OUT_OF_RANGE: mark > 100
    row_range = "STU-OR1,OR One,or1@example.com,2010-05-15,10,A,999,70,75,65,60"
    # DUPLICATE_ID: same as row_missing
    row_dup = "STU-MR1,Dupe Student,dup@example.com,2010-05-15,10,A,80,70,75,65,60"

    csv_bytes = make_csv(row_wfc, row_missing, row_invalid, row_range, row_dup)
    result = process_file(csv_bytes, "test.csv", today=TODAY)

    codes = {e.code for e in result.errors}
    assert "WRONG_FIELD_COUNT" in codes
    assert "MISSING_REQUIRED" in codes
    assert "INVALID_FORMAT" in codes
    assert "OUT_OF_RANGE" in codes
    assert "DUPLICATE_ID" in codes


# ── 7. File-level errors raise ValueError ─────────────────────────────────

def test_empty_bytes_raises():
    with pytest.raises(ValueError, match="empty"):
        process_file(b"", "test.csv", today=TODAY)


def test_null_bytes_raises():
    with pytest.raises(ValueError, match="binary"):
        process_file(b"hello\x00world", "test.csv", today=TODAY)


def test_wrong_extension_raises():
    with pytest.raises(ValueError, match="[Oo]nly .csv"):
        process_file(b"col1,col2\nval1,val2", "test.xlsx", today=TODAY)


def test_file_too_large_raises():
    big = b"x" * (MAX_FILE_SIZE + 1)
    with pytest.raises(ValueError, match="10 MB"):
        process_file(big, "test.csv", today=TODAY)


def test_missing_required_column_raises():
    # CSV with a missing required column (e.g. 'maths' replaced by 'math_score')
    bad_header = "student_id,full_name,email,date_of_birth,grade_level,section,math_score,science,english,social_studies,second_language"
    csv_bytes = (bad_header + "\nSTU-001,Name,x@x.com,2010-01-01,10,A,80,70,75,65,60").encode()
    with pytest.raises(ValueError, match="[Mm]issing"):
        process_file(csv_bytes, "test.csv", today=TODAY)


def test_duplicate_header_column_raises():
    dup_header = "student_id,full_name,email,date_of_birth,grade_level,section,maths,maths,english,social_studies,second_language"
    csv_bytes = (dup_header + "\nSTU-001,Name,x@x.com,2010-01-01,10,A,80,80,75,65,60").encode()
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        process_file(csv_bytes, "test.csv", today=TODAY)


# ── 8. Header-only file raises ValueError ────────────────────────────────

def test_header_only_raises():
    csv_bytes = HEADER.encode("utf-8")
    with pytest.raises(ValueError, match="[Hh]eader|[Oo]nly"):
        process_file(csv_bytes, "test.csv", today=TODAY)

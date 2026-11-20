"""
Exhaustive parametrised tests for all 7 validator functions in
app.importer.validators.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.importer.validators import (
    validate_student_id,
    validate_full_name,
    validate_email,
    validate_date_of_birth,
    validate_grade_level,
    validate_section,
    validate_mark,
)

TODAY = date(2026, 11, 20)


# ───────────────────────────── validate_student_id ─────────────────────────

class TestValidateStudentId:

    @pytest.mark.parametrize("raw, expected", [
        ("ABC",    "ABC"),
        ("abc",    "ABC"),          # uppercased
        ("  abc ", "ABC"),          # trimmed
        ("STU-001", "STU-001"),
        ("a1b",   "A1B"),
        ("A" * 20, "A" * 20),      # max length
        ("A-B",   "A-B"),           # hyphens allowed
    ])
    def test_valid(self, raw, expected):
        val, err = validate_student_id(raw)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",          "MISSING_REQUIRED"),
        ("   ",       "MISSING_REQUIRED"),
        ("AB",        "INVALID_FORMAT"),    # too short
        ("A" * 21,    "INVALID_FORMAT"),    # too long
        ("AB@C",      "INVALID_FORMAT"),    # invalid char
        ("AB CD",     "INVALID_FORMAT"),    # space
    ])
    def test_invalid(self, raw, code):
        val, err = validate_student_id(raw)
        assert val is None
        assert err is not None
        assert err[0] == "student_id"
        assert err[1] == code


# ───────────────────────────── validate_full_name ──────────────────────────

class TestValidateFullName:

    @pytest.mark.parametrize("raw, expected", [
        ("Jo",           "Jo"),             # min 2
        ("  Alice  Bob ", "Alice Bob"),      # trim + collapse
        ("A" * 100,      "A" * 100),        # max length
        ("Mary Jane",    "Mary Jane"),
    ])
    def test_valid(self, raw, expected):
        val, err = validate_full_name(raw)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",          "MISSING_REQUIRED"),
        ("   ",       "MISSING_REQUIRED"),
        ("A",         "OUT_OF_RANGE"),       # too short
        ("A" * 101,   "OUT_OF_RANGE"),       # too long
    ])
    def test_invalid(self, raw, code):
        val, err = validate_full_name(raw)
        assert val is None
        assert err is not None
        assert err[0] == "full_name"
        assert err[1] == code


# ───────────────────────────── validate_email ──────────────────────────────

class TestValidateEmail:

    @pytest.mark.parametrize("raw, expected", [
        ("Alice@Example.COM", "alice@example.com"),   # lowercased
        ("  user@host.io  ",  "user@host.io"),         # trimmed
        ("a+b@c.d",           "a+b@c.d"),
    ])
    def test_valid(self, raw, expected):
        val, err = validate_email(raw)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",              "MISSING_REQUIRED"),
        ("   ",           "MISSING_REQUIRED"),
        ("noatsign",      "INVALID_FORMAT"),
        ("@missing.user", "INVALID_FORMAT"),
        ("user@",         "INVALID_FORMAT"),
        ("user@host",     "INVALID_FORMAT"),    # no dot after @
        ("a @b.c",        "INVALID_FORMAT"),    # space
    ])
    def test_invalid(self, raw, code):
        val, err = validate_email(raw)
        assert val is None
        assert err is not None
        assert err[0] == "email"
        assert err[1] == code


# ───────────────────────────── validate_date_of_birth ──────────────────────

class TestValidateDateOfBirth:

    @pytest.mark.parametrize("raw, expected", [
        ("2016-11-20", date(2016, 11, 20)),   # age 10
        ("2010-05-15", date(2010, 5, 15)),     # age 16
        ("15/05/2010", date(2010, 5, 15)),     # DD/MM/YYYY
        ("2001-11-20", date(2001, 11, 20)),    # age 25 exactly
        ("2021-11-20", date(2021, 11, 20)),    # age 5 exactly
    ])
    def test_valid(self, raw, expected):
        val, err = validate_date_of_birth(raw, today=TODAY)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",              "MISSING_REQUIRED"),
        ("   ",           "MISSING_REQUIRED"),
        ("not-a-date",    "INVALID_FORMAT"),
        ("2010/05/15",    "INVALID_FORMAT"),    # wrong separator
        ("05-15-2010",    "INVALID_FORMAT"),    # MM-DD-YYYY not accepted
        ("2010-13-01",    "INVALID_FORMAT"),    # invalid month
        ("2010-02-30",    "INVALID_FORMAT"),    # impossible date
        ("30/02/2010",    "INVALID_FORMAT"),    # impossible date DD/MM/YYYY
    ])
    def test_invalid_format(self, raw, code):
        val, err = validate_date_of_birth(raw, today=TODAY)
        assert val is None
        assert err is not None
        assert err[0] == "date_of_birth"
        assert err[1] == code

    @pytest.mark.parametrize("raw", [
        "2000-11-19",   # age 26 (too old)
        "2022-11-21",   # age 3 (too young — birthday tomorrow, would be 4)
    ])
    def test_out_of_range_age(self, raw):
        val, err = validate_date_of_birth(raw, today=TODAY)
        assert val is None
        assert err is not None
        assert err[0] == "date_of_birth"
        assert err[1] == "OUT_OF_RANGE"


# ───────────────────────────── validate_grade_level ────────────────────────

class TestValidateGradeLevel:

    @pytest.mark.parametrize("raw, expected", [
        ("1",   1),
        ("12",  12),
        ("09",  9),     # leading zero OK
        ("01",  1),
        (" 6 ", 6),     # trimmed
    ])
    def test_valid(self, raw, expected):
        val, err = validate_grade_level(raw)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",     "MISSING_REQUIRED"),
        ("  ",   "MISSING_REQUIRED"),
        ("9th",  "INVALID_FORMAT"),
        ("ten",  "INVALID_FORMAT"),
        ("6.5",  "INVALID_FORMAT"),
        ("0",    "OUT_OF_RANGE"),
        ("13",   "OUT_OF_RANGE"),
        ("-1",   "INVALID_FORMAT"),     # has minus sign
    ])
    def test_invalid(self, raw, code):
        val, err = validate_grade_level(raw)
        assert val is None
        assert err is not None
        assert err[0] == "grade_level"
        assert err[1] == code


# ───────────────────────────── validate_section ────────────────────────────

class TestValidateSection:

    @pytest.mark.parametrize("raw, expected", [
        ("A", "A"),
        ("a", "A"),     # uppercased
        (" b ", "B"),   # trimmed
        ("f", "F"),
    ])
    def test_valid(self, raw, expected):
        val, err = validate_section(raw)
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",    "MISSING_REQUIRED"),
        ("  ",  "MISSING_REQUIRED"),
        ("Z",   "INVALID_FORMAT"),
        ("G",   "INVALID_FORMAT"),
        ("AB",  "INVALID_FORMAT"),    # multi-char
        ("1",   "INVALID_FORMAT"),
    ])
    def test_invalid(self, raw, code):
        val, err = validate_section(raw)
        assert val is None
        assert err is not None
        assert err[0] == "section"
        assert err[1] == code


# ───────────────────────────── validate_mark ───────────────────────────────

class TestValidateMark:

    @pytest.mark.parametrize("raw, expected", [
        ("0",     0.0),
        ("100",   100.0),
        ("85",    85.0),
        ("72.5",  72.5),
        ("0.0",   0.0),
        ("99.99", 99.99),
    ])
    def test_valid(self, raw, expected):
        val, err = validate_mark(raw, "maths")
        assert val == expected
        assert err is None

    @pytest.mark.parametrize("raw, code", [
        ("",       "MISSING_REQUIRED"),
        ("  ",     "MISSING_REQUIRED"),
        ("N/A",    "INVALID_FORMAT"),
        ("eighty", "INVALID_FORMAT"),
        ("82/100", "INVALID_FORMAT"),
        ("1e3",    "INVALID_FORMAT"),
        ("+80",    "INVALID_FORMAT"),
        ("nan",    "INVALID_FORMAT"),
        ("inf",    "INVALID_FORMAT"),
        ("-5",     "INVALID_FORMAT"),
        ("100.01", "OUT_OF_RANGE"),
        ("101",    "OUT_OF_RANGE"),
    ])
    def test_invalid(self, raw, code):
        val, err = validate_mark(raw, "science")
        assert val is None
        assert err is not None
        assert err[0] == "science"
        assert err[1] == code

    def test_field_name_propagated(self):
        """The field_name argument should appear in the error tuple."""
        _, err = validate_mark("", "english")
        assert err[0] == "english"

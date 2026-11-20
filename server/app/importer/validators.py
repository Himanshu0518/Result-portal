"""
Per-field validation functions.

All functions:
  - Accept a raw string value (already stripped once by the caller).
  - Return (normalised_value, None) on success.
  - Return (None, (field_name, code, message)) on failure.
  - Are pure: no DB, no network, no I/O.

The 'today' parameter is injectable so tests do not rot.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional


# ---------------------------------------------------------------------------
# student_id
# ---------------------------------------------------------------------------

_STUDENT_ID_RE = re.compile(r'^[A-Za-z0-9\-]{3,20}$')


def validate_student_id(raw: str) -> tuple[Optional[str], Optional[tuple]]:
    val = raw.strip().upper()
    if not val:
        return None, ("student_id", "MISSING_REQUIRED", "Student ID is required.")
    if not _STUDENT_ID_RE.match(val):
        return None, (
            "student_id",
            "INVALID_FORMAT",
            f"Student ID '{raw.strip()}' must be 3-20 characters, letters/digits/hyphens only.",
        )
    return val, None


# ---------------------------------------------------------------------------
# full_name
# ---------------------------------------------------------------------------

_COLLAPSE_SPACES = re.compile(r' +')


def validate_full_name(raw: str) -> tuple[Optional[str], Optional[tuple]]:
    val = _COLLAPSE_SPACES.sub(' ', raw.strip())
    if not val:
        return None, ("full_name", "MISSING_REQUIRED", "Full name is required.")
    if len(val) < 2 or len(val) > 100:
        return None, (
            "full_name",
            "OUT_OF_RANGE",
            f"Full name must be 2-100 characters (got {len(val)}).",
        )
    return val, None


# ---------------------------------------------------------------------------
# email
# ---------------------------------------------------------------------------

# Pragmatic email regex — avoids over-rejection without DNS lookups.
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def validate_email(raw: str) -> tuple[Optional[str], Optional[tuple]]:
    val = raw.strip().lower()
    if not val:
        return None, ("email", "MISSING_REQUIRED", "Email is required.")
    if not _EMAIL_RE.match(val):
        return None, ("email", "INVALID_FORMAT", f"'{raw.strip()}' is not a valid email address.")
    return val, None


# ---------------------------------------------------------------------------
# date_of_birth
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> Optional[date]:
    """Try YYYY-MM-DD then DD/MM/YYYY. Return None if neither matches."""
    s = raw.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None
    if re.match(r'^\d{2}/\d{2}/\d{4}$', s):
        try:
            day, month, year = s.split('/')
            return date(int(year), int(month), int(day))
        except (ValueError, TypeError):
            return None
    return None


def validate_date_of_birth(
    raw: str, today: Optional[date] = None
) -> tuple[Optional[date], Optional[tuple]]:
    if today is None:
        today = date.today()
    val = raw.strip()
    if not val:
        return None, ("date_of_birth", "MISSING_REQUIRED", "Date of birth is required.")
    parsed = _parse_date(val)
    if parsed is None:
        return None, (
            "date_of_birth",
            "INVALID_FORMAT",
            f"'{val}' is not a valid date. Use YYYY-MM-DD or DD/MM/YYYY.",
        )
    age = (
        today.year - parsed.year
        - ((today.month, today.day) < (parsed.month, parsed.day))
    )
    if age < 5 or age > 25:
        return None, (
            "date_of_birth",
            "OUT_OF_RANGE",
            f"Age must be between 5 and 25 (computed age: {age}).",
        )
    return parsed, None


# ---------------------------------------------------------------------------
# grade_level
# ---------------------------------------------------------------------------

def validate_grade_level(raw: str) -> tuple[Optional[int], Optional[tuple]]:
    val = raw.strip()
    if not val:
        return None, ("grade_level", "MISSING_REQUIRED", "Grade level is required.")
    # Accept leading zeros like '09'; must be all digits.
    if not re.match(r'^\d+$', val):
        return None, (
            "grade_level",
            "INVALID_FORMAT",
            f"Grade level '{val}' must be a whole number.",
        )
    grade = int(val)
    if grade < 1 or grade > 12:
        return None, (
            "grade_level",
            "OUT_OF_RANGE",
            f"Grade level {grade} is outside the allowed range 1-12.",
        )
    return grade, None


# ---------------------------------------------------------------------------
# section
# ---------------------------------------------------------------------------

def validate_section(raw: str) -> tuple[Optional[str], Optional[tuple]]:
    val = raw.strip().upper()
    if not val:
        return None, ("section", "MISSING_REQUIRED", "Section is required.")
    if len(val) != 1 or val not in 'ABCDEF':
        return None, (
            "section",
            "INVALID_FORMAT",
            f"Section '{raw.strip()}' must be one letter A-F.",
        )
    return val, None


# ---------------------------------------------------------------------------
# subject marks (shared logic)
# ---------------------------------------------------------------------------

_MARK_RE = re.compile(r'^\d+(\.\d+)?$')


def validate_mark(raw: str, field_name: str) -> tuple[Optional[float], Optional[tuple]]:
    val = raw.strip()
    if not val:
        return None, (field_name, "MISSING_REQUIRED", f"{field_name} mark is required.")
    # Strict regex: rejects nan, inf, 1e3, +80, -5, 82/100, etc.
    if not _MARK_RE.match(val):
        return None, (
            field_name,
            "INVALID_FORMAT",
            f"'{val}' is not a valid mark for {field_name}. Use a number like 85 or 72.5.",
        )
    mark = float(val)
    if mark < 0 or mark > 100:
        return None, (
            field_name,
            "OUT_OF_RANGE",
            f"{mark} is outside the allowed range 0 to 100 for {field_name}.",
        )
    return mark, None

"""
Tests for app.grading.compute_grade.

Max total = 500 (5 subjects × 100 each).
Grade thresholds by percentage of 500:
  >=80% (400) → A
  >=60% (300) → B
  >=50% (250) → C
  >=40% (200) → D
  < 40% (199) → F
Pass = percentage >= 40 (total >= 200).
"""
from __future__ import annotations

import pytest

from app.grading import compute_grade


def _grade(total: float) -> dict:
    """Helper: build equal-weight marks that sum to `total`."""
    per = total / 5
    return compute_grade(per, per, per, per, per)


@pytest.mark.parametrize(
    "total, expected_grade, expected_pass_fail",
    [
        (500, "A", "Pass"),
        (400, "A", "Pass"),   # exactly 80% — boundary
        (399, "B", "Pass"),   # just below A threshold
        (300, "B", "Pass"),   # exactly 60% — boundary
        (299, "C", "Pass"),   # just below B threshold
        (250, "C", "Pass"),   # exactly 50% — boundary
        (249, "D", "Pass"),   # just below C threshold
        (200, "D", "Pass"),   # exactly 40% — boundary (pass/fail line)
        (199, "F", "Fail"),   # just below 40% — fails
        (0,   "F", "Fail"),
    ],
)
def test_grade_boundaries(total: float, expected_grade: str, expected_pass_fail: str):
    result = _grade(total)
    assert result["total"] == pytest.approx(total)
    assert result["percentage"] == pytest.approx(total / 500 * 100)
    assert result["grade"] == expected_grade
    assert result["pass_fail"] == expected_pass_fail


def test_all_hundred():
    result = compute_grade(100, 100, 100, 100, 100)
    assert result["total"] == 500
    assert result["percentage"] == 100.0
    assert result["grade"] == "A"
    assert result["pass_fail"] == "Pass"


def test_fractional_marks():
    result = compute_grade(80, 60, 70, 55, 45)
    assert result["total"] == pytest.approx(310)
    assert result["grade"] == "B"
    assert result["pass_fail"] == "Pass"

"""
Grading logic.

Total = sum of 5 subjects (out of 500).
Percentage = total / 500 * 100 (unrounded for grade decision).
Grade: >=80 A, 60-79.99 B, 50-59.99 C, 40-49.99 D, <40 F.
Pass = percentage >= 40.
Display percentage to 1 decimal place.
Computed on read; never stored.
"""
from __future__ import annotations


def compute_grade(
    maths: float,
    science: float,
    english: float,
    social_studies: float,
    second_language: float,
) -> dict:
    """
    Returns a dict with keys:
        total        float  sum of 5 subjects (0-500)
        percentage   float  total / 500 * 100 (unrounded)
        grade        str    A/B/C/D/F
        pass_fail    str    "Pass" or "Fail"
    """
    total = maths + science + english + social_studies + second_language
    percentage = total / 500 * 100

    if percentage >= 80:
        grade = "A"
    elif percentage >= 60:
        grade = "B"
    elif percentage >= 50:
        grade = "C"
    elif percentage >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "total": total,
        "percentage": percentage,
        "grade": grade,
        "pass_fail": "Pass" if percentage >= 40 else "Fail",
    }

"""
CSV parsing and header normalisation.

Row numbering rules (from spec):
- Header row = line 1.
- Blank lines still advance the line counter.
- Blank lines are skipped and NOT counted in rows_read.
- Row number is the FILE line number, not the logical record number.
"""
from __future__ import annotations

import csv
import io
from typing import Iterator


REQUIRED_COLUMNS = [
    "student_id",
    "full_name",
    "email",
    "date_of_birth",
    "grade_level",
    "section",
    "maths",
    "science",
    "english",
    "social_studies",
    "second_language",
]


def _normalise_header(name: str) -> str:
    """Lower-case, strip spaces."""
    return name.strip().lower().replace(" ", "")


def parse_csv(
    text: str,
) -> tuple[list[str], Iterator[tuple[int, list[str], dict, int]]]:
    """
    Parse a CSV text string.

    Returns:
        (fieldnames, row_iterator)

        fieldnames  — normalised column names from the header row.
        row_iterator — yields (line_number, raw_field_list, col_index, num_expected)
                       for every non-blank, non-header line.  line_number is the
                       1-based file line number (blank lines advance it).

    Raises:
        ValueError for file-level problems (empty file, header-only, missing
        columns, duplicate header names).
    """
    # csv.reader needs newline='' but we already have a string; just wrap it.
    reader = csv.reader(io.StringIO(text, newline=""))

    # Read the header.
    try:
        raw_header = next(reader)
    except StopIteration:
        raise ValueError("The file is empty (no header row found).")

    if not any(h.strip() for h in raw_header):
        raise ValueError("The file is empty (no header row found).")

    normalised_header = [_normalise_header(h) for h in raw_header]

    # Check for duplicate column names.
    seen: set[str] = set()
    duplicates: list[str] = []
    for col in normalised_header:
        if col in seen:
            duplicates.append(col)
        seen.add(col)
    if duplicates:
        raise ValueError(
            f"Duplicate column name(s) after normalisation: {', '.join(duplicates)}."
        )

    # Check for required columns.
    missing = [c for c in REQUIRED_COLUMNS if c not in seen]
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing)}."
        )

    # Build column-index map (only the required columns we care about).
    # Extra columns (like parent_phone) are silently ignored.
    col_index: dict[str, int] = {}
    for col in REQUIRED_COLUMNS:
        col_index[col] = normalised_header.index(col)

    num_expected = len(raw_header)  # total columns including extras

    def _row_generator() -> Iterator[tuple[int, list[str], dict, int]]:
        line_number = 1  # header was line 1; we start data at line 2
        for raw_row in reader:
            line_number += 1
            # Blank / all-whitespace row: advance line number, skip.
            if not any(cell.strip() for cell in raw_row) and len(raw_row) <= 1:
                continue
            yield line_number, raw_row, col_index, num_expected

    return normalised_header, _row_generator()

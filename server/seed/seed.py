"""
Seed script: generates a synthetic student CSV for import testing.

Usage:
    uv run python -m seed.seed --rows 5000 --seed 42 --out data/seed.csv
    uv run python -m seed.seed --rows 5000 --seed 42 --out data/seed.csv --load
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import random
import re
from pathlib import Path

from faker import Faker

SUBJECTS = ["maths", "science", "english", "social_studies", "second_language"]
SECTIONS = list("ABCDEF")
HEADER = [
    "student_id", "full_name", "email", "date_of_birth",
    "grade_level", "section",
    "maths", "science", "english", "social_studies", "second_language",
]


def _make_email(name: str) -> str:
    slug = re.sub(r"[^a-z]", "", name.lower())
    return f"{slug}@school.edu"


def _random_dob(today: datetime.date) -> datetime.date:
    age_days = random.randint(8 * 365, 18 * 365)
    return today - datetime.timedelta(days=age_days)


def generate(rows: int, seed_value: int, out_path: Path) -> dict:
    fake = Faker("en_IN")
    Faker.seed(seed_value)
    random.seed(seed_value)

    today = datetime.date.today()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fault_counts: dict[str, int] = {
        "bad_email": 0,
        "out_of_range_mark": 0,
        "na_mark": 0,
        "bad_date": 0,
        "wrong_field_count": 0,
        "duplicate_id": 0,
        "blank_line": 0,
        "bad_section": 0,
        "out_of_range_grade": 0,
        "missing_name": 0,
    }

    written_ids: list[str] = []
    lines_written = 0

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(HEADER)

    for n in range(1, rows + 1):
        student_id = f"STU{n:05d}"
        full_name = fake.name()
        email = _make_email(full_name)
        dob = _random_dob(today).isoformat()
        grade_level: int | str = random.randint(1, 12)
        section = random.choice(SECTIONS)
        marks: list[int | str] = [random.randint(20, 100) for _ in SUBJECTS]

        # --- Fault injection ---

        if random.random() < 0.012 and written_ids:
            student_id = random.choice(written_ids)
            fault_counts["duplicate_id"] += 1

        if random.random() < 0.01:
            email = "not-an-email"
            fault_counts["bad_email"] += 1

        if random.random() < 0.01:
            marks[random.randint(0, len(marks) - 1)] = 150
            fault_counts["out_of_range_mark"] += 1

        if random.random() < 0.005:
            marks[random.randint(0, len(marks) - 1)] = "N/A"
            fault_counts["na_mark"] += 1

        if random.random() < 0.005:
            dob = "tomorrow"
            fault_counts["bad_date"] += 1

        if random.random() < 0.003:
            section = "Z"
            fault_counts["bad_section"] += 1

        if random.random() < 0.003:
            grade_level = 0
            fault_counts["out_of_range_grade"] += 1

        if random.random() < 0.003:
            full_name = ""
            fault_counts["missing_name"] += 1

        blank_before = random.random() < 0.002
        if blank_before:
            buf.write("\r\n")
            fault_counts["blank_line"] += 1
            lines_written += 1

        row: list = [
            student_id, full_name, email, dob,
            grade_level, section,
        ] + list(marks)

        if random.random() < 0.003:
            row.append("EXTRA")
            fault_counts["wrong_field_count"] += 1

        writer.writerow(row)
        lines_written += 1
        written_ids.append(f"STU{n:05d}")

    raw = buf.getvalue().encode("utf-8-sig")
    out_path.write_bytes(raw)

    manifest = {
        "rows_in_file": rows,
        "blank_lines_injected": fault_counts["blank_line"],
        "fault_counts": fault_counts,
        "seed_used": seed_value,
    }
    manifest_path = out_path.parent / "seed_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def load_csv(out_path: Path) -> None:
    from app.importer.pipeline import process_file
    from app.services.import_service import persist_import
    from app.config.db import SessionLocal

    raw_bytes = out_path.read_bytes()
    filename = out_path.name

    pipeline_result = process_file(raw_bytes, filename)

    db = SessionLocal()
    try:
        import_record = persist_import(db, raw_bytes, filename, pipeline_result)
    finally:
        db.close()

    print("Import summary:")
    print(f"  rows_read     : {import_record.rows_read}")
    print(f"  new_count     : {import_record.new_count}")
    print(f"  updated_count : {import_record.updated_count}")
    print(f"  unchanged_count: {import_record.unchanged_count}")
    print(f"  rejected_count: {import_record.rejected_count}")
    print(f"  problem_count : {import_record.problem_count}")
    print(f"  encoding_note : {import_record.encoding_note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic student seed data.")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/seed.csv")
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()

    out_path = Path(args.out)
    manifest = generate(args.rows, args.seed, out_path)

    print(f"Wrote {manifest['rows_in_file']} rows to {out_path}")
    print(f"Manifest: {out_path.parent / 'seed_manifest.json'}")
    print(f"Faults injected: {manifest['fault_counts']}")

    if args.load:
        load_csv(out_path)


if __name__ == "__main__":
    main()

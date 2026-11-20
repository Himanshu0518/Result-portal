"""
Seed script for the Result Portal database.

Creates tables (if missing), inserts a fake import record, and seeds 50
students with realistic, varied data.  The script is **idempotent**: running
it again will not error or create duplicates — existing rows are merged
(INSERT-or-update) via SQLAlchemy's ``merge()``.

Usage
-----
    cd server
    python -m seed.seed          # or: uv run python -m seed.seed
"""
from __future__ import annotations

import hashlib
import sys
from collections import Counter
from datetime import date, datetime

from sqlalchemy import inspect

# ── App imports ───────────────────────────────────────────────────────────────
from app.config.db import Base, SessionLocal, engine
from app.models import Import, Student  # noqa: F401 — registers tables

# ── Constants ─────────────────────────────────────────────────────────────────
SECTIONS = ("A", "B", "C", "D", "E", "F")

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Ananya", "Diya", "Ishaan", "Kavya",
    "Arjun", "Meera", "Rohan", "Sanya", "Tanvi", "Vihaan", "Zara",
    "Kabir", "Nisha", "Pranav", "Riya", "Sahil", "Tara",
    "Arnav", "Bhavya", "Chirag", "Devika", "Eshan",
    "Fatima", "Gaurav", "Harsh", "Ira", "Jatin",
    "Kiran", "Lakshmi", "Manav", "Neha", "Om",
    "Pooja", "Qasim", "Rahul", "Sneha", "Tushar",
    "Uma", "Varun", "Waris", "Yash", "Zoya",
    "Aisha", "Bharat", "Chetan", "Deepa", "Eshwar",
]

LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Reddy", "Nair", "Joshi",
    "Verma", "Iyer", "Chopra", "Das", "Mehta", "Gupta", "Bhat",
    "Rao", "Kapoor", "Pillai", "Saxena", "Malhotra", "Desai",
    "Hegde", "Kulkarni", "Mukherjee", "Menon", "Thakur",
    "Shah", "Banerjee", "Pandey", "Srinivasan", "Agarwal",
    "Mishra", "Chandra", "Deshpande", "Bhatt", "Shetty",
    "Nath", "Rawat", "Khanna", "Dhawan", "Bose",
    "Sen", "Tiwari", "Mahajan", "Rajan", "Kohli",
    "Chawla", "Sethi", "Bajaj", "Dutta", "Jain",
]

# Mark profiles designed to give a realistic spread of grades:
#   A (≥80%), B (60-79%), C (50-59%), D (40-49%), F (<40%)
# Each tuple: (maths, science, english, social_studies, second_language)
MARK_PROFILES: list[tuple[float, float, float, float, float]] = [
    # --- A-grade students (≥80%) --- 10 students
    (95, 92, 88, 90, 85),
    (82, 80, 85, 83, 81),
    (90, 88, 92, 86, 94),
    (88, 85, 80, 82, 90),
    (100, 95, 98, 97, 100),
    (84, 82, 80, 86, 88),
    (91, 89, 87, 93, 85),
    (80, 83, 81, 80, 82),
    (96, 94, 90, 88, 92),
    (85, 87, 84, 80, 89),
    # --- B-grade students (60-79%) --- 12 students
    (75, 72, 68, 70, 65),
    (60, 62, 65, 63, 61),
    (78, 70, 65, 72, 68),
    (65, 68, 72, 60, 70),
    (70, 75, 68, 66, 71),
    (73, 60, 62, 78, 67),
    (68, 65, 70, 74, 63),
    (77, 72, 69, 71, 75),
    (62, 64, 66, 60, 68),
    (74, 70, 72, 76, 73),
    (66, 63, 60, 65, 61),
    (79, 78, 75, 73, 70),
    # --- C-grade students (50-59%) --- 10 students
    (55, 52, 50, 58, 53),
    (50, 55, 48, 60, 52),
    (58, 50, 52, 54, 56),
    (52, 48, 55, 50, 53),
    (56, 54, 50, 52, 58),
    (50, 52, 56, 54, 50),
    (53, 50, 55, 58, 52),
    (57, 55, 50, 48, 56),
    (54, 52, 58, 50, 55),
    (50, 56, 53, 52, 54),
    # --- D-grade students (40-49%) --- 10 students
    (45, 42, 38, 48, 40),
    (40, 44, 42, 38, 46),
    (38, 40, 45, 42, 44),
    (42, 38, 40, 48, 41),
    (48, 45, 35, 40, 42),
    (40, 42, 44, 40, 38),
    (44, 38, 42, 46, 40),
    (46, 40, 38, 42, 44),
    (41, 43, 40, 38, 48),
    (43, 40, 42, 44, 41),
    # --- F-grade students (<40%) --- 8 students
    (25, 30, 20, 35, 28),
    (10, 15, 20, 12, 18),
    (35, 32, 30, 28, 25),
    (18, 22, 15, 20, 10),
    (30, 25, 28, 32, 20),
    (5, 10, 8, 12, 15),
    (20, 18, 25, 22, 30),
    (0, 5, 10, 8, 12),
]

# Dates of birth spread from 2001 to 2021 (ages ~5–25 relative to 2026)
_BIRTH_DATES = [
    date(2001, 3, 15), date(2001, 8, 22), date(2002, 1, 10), date(2002, 6, 5),
    date(2003, 4, 18), date(2003, 11, 30), date(2004, 2, 14), date(2004, 7, 7),
    date(2005, 5, 25), date(2005, 12, 3), date(2006, 1, 20), date(2006, 9, 11),
    date(2007, 3, 8),  date(2007, 10, 16), date(2008, 4, 1),  date(2008, 11, 29),
    date(2009, 2, 22), date(2009, 7, 14), date(2010, 5, 9),  date(2010, 12, 25),
    date(2011, 6, 17), date(2011, 8, 3),  date(2012, 1, 28), date(2012, 10, 5),
    date(2013, 3, 12), date(2013, 9, 19), date(2014, 2, 7),  date(2014, 7, 23),
    date(2015, 4, 30), date(2015, 11, 15), date(2016, 1, 1),  date(2016, 6, 20),
    date(2017, 3, 5),  date(2017, 8, 18), date(2018, 2, 11), date(2018, 9, 27),
    date(2019, 1, 15), date(2019, 5, 22), date(2019, 10, 8), date(2019, 12, 31),
    date(2020, 3, 14), date(2020, 7, 9),  date(2020, 11, 2), date(2021, 1, 19),
    date(2021, 4, 6),  date(2021, 6, 30), date(2021, 8, 15), date(2021, 10, 10),
    date(2021, 11, 25), date(2021, 12, 20),
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _grade_letter(percentage: float) -> str:
    if percentage >= 80:
        return "A"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C"
    if percentage >= 40:
        return "D"
    return "F"


def _build_students(import_id: int) -> list[Student]:
    """Return 50 Student instances with deterministic, varied data."""
    students: list[Student] = []

    for i in range(50):
        idx = i + 1
        student_id = f"STU-{idx:03d}"

        first = FIRST_NAMES[i]
        last = LAST_NAMES[i]
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}@school.edu"

        grade_level = (i % 12) + 1  # cycles 1-12
        section = SECTIONS[i % 6]   # cycles A-F

        maths, science, english, social_studies, second_language = MARK_PROFILES[i]
        dob = _BIRTH_DATES[i]

        students.append(
            Student(
                student_id=student_id,
                full_name=full_name,
                email=email,
                date_of_birth=dob,
                grade_level=grade_level,
                section=section,
                maths=maths,
                science=science,
                english=english,
                social_studies=social_studies,
                second_language=second_language,
                last_import_id=import_id,
            )
        )

    return students


def _build_import() -> Import:
    """Return a realistic Import audit record whose counts add up."""
    # 50 rows read: 48 new + 0 updated + 0 unchanged + 2 rejected = 50 ✓
    fake_hash = hashlib.sha256(b"seed-data-v1").hexdigest()
    return Import(
        filename="seed_data.csv",
        file_sha256=fake_hash,
        size_bytes=4_096,
        rows_read=50,
        new_count=48,
        updated_count=0,
        unchanged_count=0,
        rejected_count=2,
        problem_count=3,
        encoding_note=None,
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("🌱 Result Portal — seed script")
    print("=" * 44)

    # 1. Create tables if they don't exist
    Base.metadata.create_all(engine)
    print("✔ Tables verified / created")

    db = SessionLocal()
    try:
        # 2. Seed import record (idempotent via merge on PK)
        imp = _build_import()
        # Check if a seed import already exists by filename
        existing_import = (
            db.query(Import)
            .filter(Import.filename == "seed_data.csv")
            .first()
        )
        if existing_import:
            import_id = existing_import.id
            print(f"✔ Import record already exists (id={import_id}), reusing")
        else:
            db.add(imp)
            db.flush()  # assigns imp.id
            import_id = imp.id
            print(f"✔ Import record created (id={import_id})")

        # 3. Seed students (idempotent via merge — updates if PK exists)
        students = _build_students(import_id)
        for stu in students:
            db.merge(stu)

        db.commit()
        print(f"✔ {len(students)} students seeded (merged)\n")

        # 4. Summary
        all_students = db.query(Student).all()
        grade_dist: Counter[str] = Counter()
        for s in all_students:
            total = s.maths + s.science + s.english + s.social_studies + s.second_language
            pct = total / 500 * 100
            grade_dist[_grade_letter(pct)] += 1

        print(f"📊 Summary: {len(all_students)} students in database")
        print("-" * 30)
        for letter in ("A", "B", "C", "D", "F"):
            count = grade_dist.get(letter, 0)
            bar = "█" * count
            print(f"  Grade {letter}: {count:>3}  {bar}")
        print("-" * 30)

        # Grade-level distribution
        level_dist: Counter[int] = Counter()
        for s in all_students:
            level_dist[s.grade_level] += 1
        print("\n📚 Grade-level distribution:")
        for lvl in sorted(level_dist):
            print(f"  Level {lvl:>2}: {level_dist[lvl]} students")

        pass_count = sum(
            1 for s in all_students
            if (s.maths + s.science + s.english + s.social_studies + s.second_language) / 500 * 100 >= 40
        )
        fail_count = len(all_students) - pass_count
        print(f"\n✅ Pass: {pass_count}  |  ❌ Fail: {fail_count}")
        print("\n🎉 Seed complete!")

    except Exception:
        db.rollback()
        print("❌ Seed failed — rolled back", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

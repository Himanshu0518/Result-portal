"""
Import audit and row-error models.

imports        one row per uploaded file (audit trail + summary counts)
import_errors  one row per problem found during parsing/validation
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.db import Base


ERROR_CODES = (
    "MISSING_REQUIRED",
    "INVALID_FORMAT",
    "OUT_OF_RANGE",
    "DUPLICATE_ID",
    "WRONG_FIELD_COUNT",
)

# Build the SQL IN-list once so the CheckConstraint expression is readable.
_error_codes_sql = ", ".join(f"'{c}'" for c in ERROR_CODES)


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # detects re-uploads
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Row-level counters (blank lines excluded from rows_read per spec).
    rows_read: Mapped[int] = mapped_column(Integer, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # problem_count >= rejected_count because one row can produce several errors.
    problem_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Non-null only when encoding was guessed (e.g. "guessed cp1252").
    encoding_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    errors: Mapped[list["ImportError"]] = relationship(
        back_populates="import_",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "rows_read >= 0 AND new_count >= 0 AND updated_count >= 0 "
            "AND unchanged_count >= 0 AND rejected_count >= 0 AND problem_count >= 0",
            name="ck_imports_counts_non_negative",
        ),
        # Every non-rejected row is exactly one of: new, updated, unchanged.
        CheckConstraint(
            "new_count + updated_count + unchanged_count + rejected_count = rows_read",
            name="ck_imports_counts_add_up",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Import id={self.id} file={self.filename!r} "
            f"rows={self.rows_read} new={self.new_count} rejected={self.rejected_count}>"
        )


class ImportError(Base):
    """One row per problem found in an import.  Errors are always stored in full
    (not capped at 50) because the UI paginates them and the bonus CSV download
    needs them all."""

    __tablename__ = "import_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("imports.id", ondelete="CASCADE"), nullable=False
    )
    # File line number; header = 1; blank lines still advance this counter.
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Raw value from the file — may be junk or blank; NULL means the whole row failed.
    student_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Which column caused the problem; NULL means the whole row (e.g. WRONG_FIELD_COUNT).
    field: Mapped[str | None] = mapped_column(String(32), nullable=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Plain-English message shown directly in the admin UI.
    message: Mapped[str] = mapped_column(String(500), nullable=False)

    import_: Mapped["Import"] = relationship(back_populates="errors")

    __table_args__ = (
        CheckConstraint(
            f"code IN ({_error_codes_sql})",
            name="ck_import_errors_code",
        ),
        # Composite index used by paginated error listing and CSV export.
        Index("ix_import_errors_import_row", "import_id", "row_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImportError import={self.import_id} row={self.row_number} "
            f"code={self.code!r} field={self.field!r}>"
        )

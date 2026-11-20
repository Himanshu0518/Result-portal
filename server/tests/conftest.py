"""
Shared pytest fixtures for the Result Portal test suite.

Provides:
- In-memory SQLite DB (test_db_session)
- FastAPI TestClient wired to that DB (client)
- Helper to build CSV bytes from rows (make_csv)
"""
from __future__ import annotations

import sys
import os
from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure the server package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config.db import Base, get_db
from app.models import Student, Import, ImportError  # noqa: F401 — registers tables
from main import app


# ---------------------------------------------------------------------------
# In-memory SQLite engine + session
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_engine():
    # StaticPool forces all ORM sessions to reuse the same underlying
    # SQLite connection, so the in-memory database created by create_all()
    # is visible to every subsequent query within the same test.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def test_db_session(test_engine) -> Generator[Session, None, None]:
    TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine) -> Generator[TestClient, None, None]:
    """TestClient whose DB dependency points to the in-memory SQLite."""
    TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CSV helper
# ---------------------------------------------------------------------------

HEADER = "student_id,full_name,email,date_of_birth,grade_level,section,maths,science,english,social_studies,second_language"

VALID_ROW = "STU-001,Alice Smith,alice@example.com,2010-05-15,10,A,85,78,92,88,76"


def make_csv(*rows: str, header: str = HEADER) -> bytes:
    """Build CSV bytes from a header + data rows."""
    lines = [header] + list(rows)
    return "\n".join(lines).encode("utf-8")

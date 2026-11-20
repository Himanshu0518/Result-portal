"""
Integration tests for the FastAPI endpoints.

Uses the `client` fixture from conftest (TestClient backed by in-memory SQLite).
Uses `make_csv` from conftest to build CSV payloads.
"""
from __future__ import annotations

import io

import pytest

from tests.conftest import make_csv, VALID_ROW, HEADER


# ── Helpers ───────────────────────────────────────────────────────────────

def _upload(client, csv_bytes: bytes, filename: str = "test.csv"):
    """POST /api/imports with the given bytes."""
    return client.post(
        "/api/imports",
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
    )


# ── 1. Health check ───────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── 2. POST /api/imports — valid CSV ─────────────────────────────────────

def test_upload_valid_csv(client):
    csv_bytes = make_csv(VALID_ROW)
    r = _upload(client, csv_bytes)
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    summary = body["data"]["summary"]
    assert summary["rows_read"] == 1
    assert summary["new_count"] == 1


# ── 3. POST /api/imports — binary file → 422 UNPROCESSABLE_FILE ──────────

def test_upload_binary_file(client):
    r = _upload(client, b"hello\x00world", filename="test.csv")
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNPROCESSABLE_FILE"


# ── 4. POST /api/imports — missing required column → 422 ─────────────────

def test_upload_missing_column(client):
    bad_header = "student_id,full_name,email,date_of_birth,grade_level,section,math_score,science,english,social_studies,second_language"
    csv_bytes = (bad_header + "\nSTU-001,Test Student,t@t.com,2010-01-01,10,A,80,70,75,65,60").encode()
    r = _upload(client, csv_bytes)
    assert r.status_code == 422


# ── 5. Upload same file twice — second has new_count=0, unchanged_count>0 ─

def test_upload_same_file_twice(client):
    csv_bytes = make_csv(VALID_ROW)

    r1 = _upload(client, csv_bytes)
    assert r1.status_code == 201
    s1 = r1.json()["data"]["summary"]
    assert s1["new_count"] == 1

    r2 = _upload(client, csv_bytes)
    assert r2.status_code == 201
    s2 = r2.json()["data"]["summary"]
    assert s2["new_count"] == 0
    assert s2["unchanged_count"] > 0


# ── 6. GET /api/imports/{id} — after upload ───────────────────────────────

def test_get_import_by_id(client):
    csv_bytes = make_csv(VALID_ROW)
    r_post = _upload(client, csv_bytes)
    import_id = r_post.json()["data"]["summary"]["id"]

    r = client.get(f"/api/imports/{import_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["id"] == import_id


# ── 7. GET /api/imports/{id}/errors — paginated ───────────────────────────

def test_get_import_errors_paginated(client):
    # Upload a file with one bad row to get at least one error.
    bad_row = "STU-E01,,bad-email,2010-05-15,10,A,80,70,75,65,60"
    csv_bytes = make_csv(bad_row)
    r_post = _upload(client, csv_bytes)
    import_id = r_post.json()["data"]["summary"]["id"]

    r = client.get(f"/api/imports/{import_id}/errors?page=1&page_size=50")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "meta" in body
    assert body["meta"]["total"] >= 1
    assert isinstance(body["data"], list)


# ── 8. GET /api/imports/999 — nonexistent → 404 NOT_FOUND ────────────────

def test_get_import_not_found(client):
    r = client.get("/api/imports/999")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


# ── 9. GET /api/students — after import, items have grade field ──────────

def test_list_students_after_import(client):
    csv_bytes = make_csv(VALID_ROW)
    _upload(client, csv_bytes)

    r = client.get("/api/students")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["meta"]["total"] > 0
    item = body["data"][0]
    assert "grade" in item


# ── 10. GET /api/students?q=STU-001 — search ─────────────────────────────

def test_search_student_by_id(client):
    csv_bytes = make_csv(VALID_ROW)
    _upload(client, csv_bytes)

    r = client.get("/api/students?q=STU-001")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 1
    ids = [item["student_id"] for item in body["data"]]
    assert "STU-001" in ids


# ── 11. GET /api/students/{id} — full report ─────────────────────────────

def test_get_student_detail(client):
    csv_bytes = make_csv(VALID_ROW)
    _upload(client, csv_bytes)

    r = client.get("/api/students/STU-001")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["student_id"] == "STU-001"
    assert "grade" in data
    assert "pass_fail" in data
    assert "percentage" in data


# ── 12. GET /api/students/DOESNOTEXIST → 404 NOT_FOUND ───────────────────

def test_get_student_not_found(client):
    r = client.get("/api/students/DOESNOTEXIST")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


# ── 13. GET /api/students?grade_level=10 — filter ────────────────────────

def test_responses_carry_request_id(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers["X-Request-ID"]


def test_filter_students_by_grade_level(client):
    # VALID_ROW uses grade_level=10
    csv_bytes = make_csv(VALID_ROW)
    _upload(client, csv_bytes)

    r = client.get("/api/students?grade_level=10")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 1
    for item in body["data"]:
        assert item["grade_level"] == 10

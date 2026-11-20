# NOTES.md

## Stack and why

| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI + Python 3.13 | Typed, fast to write, strong for text-heavy data processing; `pytest` parametrisation makes the validation rules easy to test exhaustively |
| ORM | SQLAlchemy 2.0 | Readable mapped models, `INSERT OR REPLACE` for SQLite upsert, clean session-per-request with the `get_db` dependency |
| Database | SQLite (WAL mode) | Zero extra services; 5,000 rows is well under its practical ceiling; WAL mode allows concurrent reads during writes |
| Migrations | Alembic | Schema changes are tracked, reversible, and reproducible across machines |
| Frontend | React 19 + Vite + TypeScript | SPA for three screens; Vite gives fast HMR in development; TypeScript catches API shape mismatches at compile time |
| Styling | Tailwind CSS v4 + shadcn/ui | CSS-variable design tokens; shadcn gives accessible, unstyled primitives that are easy to customise without fighting a component library |
| Data fetching | TanStack Query | Loading, error, stale, and retry states come almost free; `keepPreviousData` stops the table flickering between pages |
| Search debounce | `use-debounce` | Handles React Strict Mode's double-invocation correctly; provides `useDebouncedCallback` as a free upgrade path |
| Package manager | pnpm | Faster installs, strict dependency isolation |
| Container | Multi-stage Dockerfile | Node stage builds the SPA; Python stage serves the API and static files from one container on one port |

---

## Decisions and assumptions

### What counts as a valid row

A row is valid when every field passes all rules below. One bad field rejects the whole row; every problem in that row is still recorded so the administrator sees everything at once rather than fixing one issue at a time.

| Field | Rules | Normalisation |
|---|---|---|
| `student_id` | 3–20 chars, letters/digits/hyphens | trim, upper-case |
| `full_name` | 2–100 chars after trim | trim, collapse repeated spaces |
| `email` | must match `^[^@\s]+@[^@\s]+\.[^@\s]+$` | trim, lower-case |
| `date_of_birth` | `YYYY-MM-DD` or `DD/MM/YYYY` only; real calendar date; student age 5–25 today | trim |
| `grade_level` | whole number 1–12; leading zeros (`09`) accepted | trim, to int |
| `section` | exactly one letter A–F | trim, upper-case |
| 5 subject marks | number 0–100, decimals allowed | trim, to float |

Marks use the strict regex `^\d+(\.\d+)?$`. Python's `float()` accepts `nan`, `inf`, `1e3`, and `+80` — all of which must be rejected — so it is never called on untrusted input directly.

### Duplicate students in one file

The first row to carry a given `student_id` claims it, **even if that first row is itself invalid**. Every later row with the same ID in the same file gets `DUPLICATE_ID`. This was confirmed against the expected sample totals (5,000 rows read, 4,685 imported, 315 rejected): counting only valid first rows gives 4,687 / 313, which does not match.

### Re-uploading the same file

The file's SHA-256 hash is stored with each import. If the same hash appears again the import is recorded as `0 new, 0 updated, N unchanged` and the UI shows a notice. No student data is re-written.

### Re-uploading a changed file

An upload is an **add or update, never a delete**. Students in the database who are absent from the new file are left alone. The administrator can see the counts in the import summary.

### Grading scheme

| Percentage (unrounded) | Grade |
|---|---|
| ≥ 80 | A |
| ≥ 60 | B |
| ≥ 50 | C |
| ≥ 40 | D |
| < 40 | F |

Total = sum of five subjects (out of 500). Percentage = total ÷ 500 × 100. Pass = percentage ≥ 40. Grade is computed from the **unrounded** percentage so a student at 79.96 % is not shown "80.0 % — B". Derived values are never stored; changing the scheme needs no migration.

### Bad files

All of the following return a plain-English 422 response and never a 500:

- Empty file
- Binary content (null bytes detected)
- Wrong file extension (not `.csv`)
- File over 10 MB
- Missing required column(s) — the response names which ones
- Duplicate column names after normalisation
- Non-UTF-8 content that also fails cp1252 fallback

A file that passes header validation but has only bad rows is accepted (HTTP 201) with `0` imported and a full error list. The import never crashes on a single bad row.

### Data traps noticed in the sample file

- **UTF-8 BOM** — decoded with `utf-8-sig` to strip it transparently
- **CRLF line endings** — `csv.reader` handles these when given `newline=""`
- **Extra column `parent_phone`** — ignored and not stored (personal data not required by the spec)
- **10 blank lines** — skipped, not counted in `rows_read`, but they still advance the line-number counter
- **Marks like `N/A`, `eighty`, `82/100`, `1e3`** — rejected as `INVALID_FORMAT` by the strict regex
- **Section values `a`, `  D ` (padded), `Z`** — trim and upper-case first; `Z` is then invalid
- **Grade level `07`, `9th`, `ten`** — leading zeros are accepted; non-numeric strings are `INVALID_FORMAT`
- **Date formats `DD/MM/YYYY` and `YYYY-MM-DD`** — both accepted; anything else is `INVALID_FORMAT`

---

## How large files are handled today

The import runs **synchronously** inside the HTTP request. The whole file is read into memory, validated, and written to the database in a single transaction before the response is sent.

**Why this is correct for this assignment:** the sample file is 480 KB and 5,000 rows, processing takes under a second. The frontend shows a spinner for the duration of the POST, which is the right amount of UI complexity for a sub-second operation. A background job would add a polling loop, a job-status endpoint, and in-memory job state — all complexity that serves no user at this scale.

The database write uses periodic `session.flush()` every 500 rows so the SQLAlchemy identity map stays bounded, and existing student lookups are batched in chunks of 500 to stay inside SQLite's variable-binding limit.

---

## What I would do next for large files (50 k+ rows)

The synchronous approach stops being correct when processing takes longer than a reasonable HTTP timeout (~30 s). The upgrade path:

**1. Stream the upload to disk** instead of `file.file.read()` — keeps peak memory flat regardless of file size.

**2. Accept immediately, return a job ID**

```
POST /api/imports        → 202 { "job_id": "abc123" }
GET  /api/imports/jobs/{job_id} → { "status": "processing", "progress": 42, ... }
```

**3. Process in a background worker** in chunks of ~500 rows, each chunk committed in its own transaction. FastAPI's `BackgroundTasks` works for a single process; a task queue (Celery + Redis or ARQ) is the right call for multi-worker deployments.

**4. Frontend polls** until `status === "completed"`, then fetches the import summary.

---

## SQLite to PostgreSQL

The codebase is intentionally SQLite-first for simplicity and zero-extra-services deployment. Moving to Postgres in production requires two changes:

1. Set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` in the environment.
2. Replace the `INSERT OR REPLACE` upsert in `import_service.py` with `INSERT ... ON CONFLICT (student_id) DO UPDATE SET ...` — SQLAlchemy's dialect-agnostic `insert().on_conflict_do_update()` handles this cleanly.

Everything else — models, migrations, queries, the session lifecycle — works unchanged on Postgres.

---

## What is missing

- **Authentication** — the portal has no login; it is admin-only by convention
- **Keyset pagination** — offset pagination is used throughout; at very high page numbers it degrades; keyset would fix this for large datasets
- **Per-subject pass threshold** — the current pass rule is percentage ≥ 40 overall; a minimum-per-subject rule is a common school requirement and would be straightforward to add to `grading.py`
- **Automated frontend tests** — the backend has 136 pytest tests; the frontend has none; Vitest + React Testing Library would cover the import result display and student table states

---

## AI usage

I used Kiro (an AI coding assistant built into the IDE) throughout this project. It was most useful for the mechanical and structural work: generating the initial SQLAlchemy model definitions and Pydantic schemas from the data spec, scaffolding the FastAPI router and service layer, writing the Alembic migration configuration, and producing the React component skeletons for the three pages.

I reviewed every file and can explain any part of the code.

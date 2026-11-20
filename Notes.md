# NOTES.md

## Stack and why

| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI + Python 3.13 | Typed, fast to write, excellent for data-heavy text processing; `pytest` parametrisation makes the validation rules easy to test exhaustively |
| ORM | SQLAlchemy 2.0 | Readable mapped models, supports `INSERT OR REPLACE` for SQLite upsert, clean session-per-request pattern |
| Database | SQLite (WAL mode) | Zero extra services; 5,000 rows is well under its practical ceiling; WAL mode allows concurrent reads during writes |
| Migrations | Alembic | Schema changes are tracked, reversible, and reproducible across machines |
| Frontend | React 19 + Vite + TypeScript | SPA for three screens; Vite gives instant HMR; TypeScript catches shape mismatches between API responses and UI |
| Styling | Tailwind CSS v4 + shadcn/ui | Design-token CSS variables; shadcn components are unstyled primitives — no fighting a component library |
| Data fetching | TanStack Query | Loading, error, stale and retry states come almost free; `keepPreviousData` stops the table flickering between pages |
| Package manager | pnpm | Faster installs, strict dependency isolation |
| Container | Single-stage Dockerfile | Node builds the SPA; Python serves the API and static files from one container on one port |

---

## Decisions and assumptions

### What counts as a valid row

A row is valid when every field passes all rules below. One bad field rejects the whole row; every problem in that row is still recorded so the administrator sees everything at once.

| Field | Rules | Normalisation |
|---|---|---|
| `student_id` | 3–20 chars, letters/digits/hyphens | trim, upper-case |
| `full_name` | 2–100 chars after trim | trim, collapse repeated spaces |
| `email` | must match `^[^@\s]+@[^@\s]+\.[^@\s]+$` | trim, lower-case |
| `date_of_birth` | `YYYY-MM-DD` or `DD/MM/YYYY` only; real calendar date; student age 5–25 today | trim |
| `grade_level` | whole number 1–12; leading zeros (`09`) accepted | trim, to int |
| `section` | exactly one letter A–F | trim, upper-case |
| 5 subject marks | number 0–100, decimals allowed | trim, to float |

Marks use the strict regex `^\d+(\.\d+)?$`. Python's `float()` accepts `nan`, `inf`, `1e3`, and `+80` — all of which must be rejected — so it is never called directly on untrusted input.

### Duplicate students in one file

The first row to carry a given `student_id` claims it, **even if that first row is itself invalid**. Every later row with the same ID in the same file gets `DUPLICATE_ID`. This was confirmed against the expected sample totals (5,000 rows read, 4,685 imported, 315 rejected): counting only valid first rows gives 4,687 / 313, which does not match.

### Re-uploading the same file

The file's SHA-256 hash is stored with each import. If the same hash is seen again the import is recorded as `0 new, 0 updated, N unchanged` and the UI shows a warning. No student data is re-written.

### Re-uploading a changed file

An upload is an **add or update, never a delete**. Students in the database who are absent from the new file are left alone. The administrator is told this in the import result.

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
- **CRLF line endings** — `csv.reader` handles these correctly when given `newline=""`
- **Extra column `parent_phone`** — ignored; not stored (personal data not required by the spec)
- **10 blank lines** — skipped, not counted in `rows_read`, but they still advance the line-number counter
- **Marks like `N/A`, `eighty`, `82/100`, `1e3`** — rejected as `INVALID_FORMAT` by the strict regex
- **Section values `a`, `  D ` (padded), `Z`** — trim and upper-case first; `Z` is then invalid
- **Grade level `07`, `9th`, `ten`** — leading zeros are accepted; non-numeric strings are `INVALID_FORMAT`
- **Date formats `DD/MM/YYYY` and `YYYY-MM-DD`** — both accepted; anything else is `INVALID_FORMAT`

---

## How large files are handled today

The import runs **synchronously** inside the HTTP request. The whole file is read into memory, validated, and written to the database in a single transaction before the response is sent.

**Why this is correct for this assignment:**  
The sample file is 480 KB and 5,000 rows. End-to-end processing takes under one second. The frontend shows a spinner for the duration of the POST, which is the right amount of UI complexity for a sub-second operation. A background job would add a polling loop, a job-status endpoint, and in-memory job state — all complexity that serves no user at this scale.

The database write uses periodic `session.flush()` every 500 rows so the SQLAlchemy identity map never grows unbounded, and existing student lookups are batched in chunks of 500 to stay inside SQLite's variable-binding limit.

---

## What I would do next for large files (50 k+ rows)

The synchronous approach stops being correct when processing takes longer than a reasonable HTTP timeout (~30 s). The upgrade path is straightforward:

**1. Stream the upload to disk instead of reading it all at once**

```python
# Instead of: raw_bytes = file.file.read()
with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
    shutil.copyfileobj(file.file, tmp)
    tmp_path = tmp.name
```

This keeps peak memory flat regardless of file size.

**2. Accept the upload immediately, return a job ID**

```
POST /api/imports        → 202 { "job_id": "abc123" }
GET  /api/imports/jobs/{job_id} → { "status": "processing", "progress": 42, ... }
```

The endpoint validates only the header (fast), then hands the file path to a background worker.

**3. Process in chunks with a background task**

FastAPI's built-in `BackgroundTasks` works for a single process. For a multi-worker deployment, replace it with a task queue (Celery + Redis, or ARQ).

```python
background_tasks.add_task(run_import_job, job_id, tmp_path)
```

The worker reads the CSV in chunks of ~500 rows, validates and upserts each chunk in its own transaction, and updates a `progress` column in the `imports` table after each chunk. A partial failure rolls back only the current chunk and records the error; previously committed chunks are preserved.

**4. Frontend polls until done**

```
useQuery({ queryKey: ["job", jobId], refetchInterval: 1000, enabled: status !== "completed" })
```

Once status is `completed` the import ID is available and the full result is fetched.

---

## What is missing



## AI usage

Kiro (Anthropic's coding assistant in the IDE) was used throughout. It generated the initial scaffolding for models, validators, the importer pipeline, API routes, and the frontend component stubs. Every file was reviewed and corrected: the initial `import_service.py` had a critical bug (counts flushed before they were computed, causing a CHECK constraint failure), the background-job system it generated was removed as over-engineering for the assignment scope, and validators were audited line-by-line against the sample data. I can walk through any part of the code.

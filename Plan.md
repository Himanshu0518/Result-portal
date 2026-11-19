# Student Results Portal: Architecture, Plan and Decisions

*Es Magico full-stack intern assignment. Planning document, prepared from the assignment PDF, the sample-pack README and a profile of `students_sample.csv`.*

## 1. What the assignment is really testing

The brief says it is "short on purpose". The grading table rewards five things, so every choice below serves one of them:

| Area | What it means for us |
| --- | --- |
| Judgement and ownership | Decide the gaps, write them down, spot data traps unprompted |
| Robustness | Bad rows and bad files never crash the app; the admin is never left guessing |
| Working product | Three screens, end to end, with loading, empty and error states |
| Engineering | Readable code, tests that catch real bugs, clean commit history |
| Communication | Honest README and a one-page NOTES.md |

Principle: **a small thing that works and is well reasoned beats a large thing that does not.** Build the core first. Bonuses only after.

## 2. Data profile (what is actually in the sample file)

I profiled the 5,000-row sample. Findings, and what each implies:

| Finding | Count | Implication |
| --- | --- | --- |
| UTF-8 **with BOM**, **CRLF** line endings | whole file | Decode with `utf-8-sig`; use the `csv` module with `newline=''` |
| Extra column `parent_phone` | all rows | Ignore extra columns |
| Blank lines | 10 | Skip, do not count, but they still advance the line number |
| Wrong field count (11 or 13 fields) | 15 | Reject whole row as `WRONG_FIELD_COUNT` |
| Duplicate IDs (case-insensitive, trimmed) | 60 | First row wins, later rows `DUPLICATE_ID` |
| Dates in `YYYY-MM-DD` (3,764) and `DD/MM/YYYY` (1,206) |  | Two accepted formats only |
| Dates like `tomorrow`, `99-99-9999`, `99.99.9999` | 15 | `INVALID_FORMAT` (only two formats are allowed) |
| Grade level: `07`, `09`, `ten`, out-of-range numbers |  | Accept leading zeros; `ten` is invalid, 13 or 0 is out of range |
| Section: `a`, `  D ` (padded), `Z` |  | Trim and upper-case; `Z` is invalid |
| Marks: `N/A`, `eighty`, `abc`, `82/100`, `1e3`, blank, whitespace-only | \~60 | Blank = missing; other text = invalid format; numbers above 100 = out of range |
| Emails with surrounding spaces; truncated like `diya@` |  | Trim first, then validate shape |
| Names with padding, plus Unicode (`Zoë D'Souza`, `Bjørn Nair`, `Müller Patel`) |  | Trim, collapse spaces, never strip accents or apostrophes |

### Verification against the published totals

I implemented the rules above as a throwaway script and ran it on the sample. Result: **5,000 rows read, 4,685 imported, 315 rejected**, which matches the sample-pack README exactly. The breakdown of the 315 rejections was 154 invalid format, 49 missing, 37 out of range, 60 duplicates and 15 wrong field count.

This settled two ambiguous points. Both rules below are **confirmed by the expected totals**:

1. **Blank lines are not counted** in "rows read" (5,000 excludes the 10 blank lines).
2. **A duplicate is judged by ID alone, before validation.** The first row with an ID claims it, *even if that first row is itself invalid*. Later rows with that ID are `DUPLICATE_ID`. If we only counted valid first rows, we would get 4,687 and 313, which is wrong. Rows with the wrong field count do not claim an ID.

These two points go straight into NOTES.md as "noticed without being told".

## 3. Tech stack

**Decision: FastAPI (Python) + SQLite + React (Vite, TypeScript) SPA, built and served from one Docker container on port 8080.**

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | FastAPI, Pydantic v2 | You know it; typed request and response models; automatic OpenAPI docs help reviewers |
| Data access | SQLAlchemy 2.0 | Readable, supports `INSERT ... ON CONFLICT DO UPDATE` for SQLite |
| Database | SQLite (WAL mode), file on a Docker volume | 5,000 rows is tiny; zero extra services; the brief says "a Dockerfile", not a compose stack |
| Frontend | React + Vite + TypeScript, React Router | Three screens, admin tool, no SEO need, so Next.js adds nothing |
| Data fetching | TanStack Query | Loading, error, retry and caching states come almost free, and those states are graded |
| Styling | Tailwind CSS | Fast, consistent, matches the sketches |
| Tests | pytest (+ httpx TestClient), Vitest for a few frontend checks if time allows | One command: `make test` |
| Seed | Faker with a fixed seed | Reproducible messy data |
| Packaging | Multi-stage Dockerfile | Node stage builds the SPA; Python stage serves API and static files |

**Why not Next.js or Express?** Either works, and Next.js full-stack in one language is a fair alternative. But Python is the stronger tool for messy-text handling (encodings, number parsing, `pytest` parametrization), and the single-container SPA setup is simpler to explain and to run. If you would be much faster in TypeScript, the same design carries over unchanged: only the importer and server code move.

**Why SQLite is defensible:** the workload is one admin uploading occasionally and reading often. NOTES.md should say Postgres is the next step if there are concurrent writers or multiple servers.

## 4. Architecture

```
Browser (React SPA)
   |  /import   /students   /students/:id
   v
FastAPI  (port 8080)
   |-- /api/*            JSON API
   |-- /*                serves built SPA, falls back to index.html for client routes
   v
 importer/  (pure Python, no web or DB imports)
   decode -> parse -> validate -> dedupe -> result object
   v
 SQLite  (students, imports, import_errors)
```

Key design idea: **the importer is a pure function** from file bytes to a result object (valid rows and row problems). It touches no database and no web framework. That makes it trivially testable, and the DB write is a separate, thin step.

### Repo layout

```
results-portal/
  backend/
    app/
      main.py            app factory, static files, SPA fallback
      api/               imports.py, students.py
      importer/          decode.py, parser.py, validators.py, pipeline.py, errors.py
      grading.py         pure grading function
      models.py          SQLAlchemy models
      db.py              engine, WAL, session
      seed.py            CLI: generate and optionally load messy data
    tests/
  frontend/
    src/ pages/ (ImportPage, StudentsPage, StudentReportPage, NotFound)
          components/ api/ hooks/
  fixtures/               small CSVs used by tests
  Dockerfile
  Makefile                dev, test, seed, docker-build, docker-run
  README.md
  NOTES.md
```

## 5. Validation rules (from the sample-pack README)

These are specified, so we implement them exactly. Every rule gets table-driven tests.

| Column | Rule | Normalisation | Error codes |
| --- | --- | --- | --- |
| `student_id` | 3 to 20 chars, letters, digits, hyphen | trim, upper-case | `MISSING_REQUIRED`, `INVALID_FORMAT`, `DUPLICATE_ID` |
| `full_name` | 2 to 100 chars after trimming; any Unicode letters, apostrophes, commas | trim, collapse repeated spaces | `MISSING_REQUIRED`, `OUT_OF_RANGE` (length) |
| `email` | valid address | trim, lower-case | `MISSING_REQUIRED`, `INVALID_FORMAT` |
| `date_of_birth` | `YYYY-MM-DD` or `DD/MM/YYYY`, a real date, age 5 to 25 today | trim | `MISSING_REQUIRED`, `INVALID_FORMAT`, `OUT_OF_RANGE` |
| `grade_level` | whole number 1 to 12 (`09` fine) | trim, to int | `MISSING_REQUIRED`, `INVALID_FORMAT`, `OUT_OF_RANGE` |
| `section` | one letter A to F | trim, upper-case | `MISSING_REQUIRED`, `INVALID_FORMAT` |
| 5 subject marks | number 0 to 100, decimals allowed | trim, to float | `MISSING_REQUIRED`, `INVALID_FORMAT`, `OUT_OF_RANGE` |

**File-level rules:** header must contain all required columns (any order, any case, spaces ignored, extra columns ignored); UTF-8 with or without BOM; CRLF or LF; quoted fields may contain commas; blank and all-empty rows skipped and not counted; wrong field count rejects the whole row. Row numbers are **file line numbers, header = line 1, counting blank lines**.

### Judgement calls I recommend (write each in NOTES.md)

| Case | Decision | Reason |
| --- | --- | --- |
| Mark is blank, or whitespace only | `MISSING_REQUIRED` | Blank means absent |
| Mark is `N/A`, `eighty`, `82/100`, `1e3` | `INVALID_FORMAT` | Parse with a strict regex `^\d+(\.\d+)?$`, **not** `float()` |
| Mark is `NaN`, `inf`, `-5`, `+80` | `INVALID_FORMAT` (`-5` is a negative number, so `OUT_OF_RANGE` is also defensible; pick one and test it) | Python's `float()` accepts `nan` and `inf`, a classic trap |
| Section is `Z` or `AB` | `INVALID_FORMAT` | One consistent code for "not in the allowed shape" |
| Date `29/02/2011` | `INVALID_FORMAT` | Not a real date |
| Date `03-04-2012`, `03.04.2012` | `INVALID_FORMAT` | Only two formats are allowed; never guess |
| Age boundaries | Inclusive: exactly 5 and exactly 25 are valid, computed from the birthday against today | Use an **injectable "today"** so tests do not rot |
| Several bad fields in one row | Report **every** problem for the row, but count the row once in "rejected" | More useful to the admin; the sketch shows 348 problems for 315 rows, which hints at this |
| Duplicate or wrong-field-count row | Single problem for that row, no further checks | Nothing else about it can be trusted |
| Name contains digits | Allowed | The rule only constrains length |
| Email shape | Pragmatic regex or `email-validator` without DNS checks | Do not over-reject; no network calls |

## 6. Left-open decisions

### Duplicates and re-upload

| Case | Behaviour |
| --- | --- |
| Same ID twice in one file | First row wins; later rows `DUPLICATE_ID` |
| ID already in the database | **Upsert by `student_id`**: update the existing student |
| Same file uploaded again | Idempotent: report `0 new, 0 updated, N unchanged`, and show a note that this exact file was imported before (file hash) |
| Result counts | `rows_read`, `imported` (= new + updated + unchanged), `new`, `updated`, `unchanged`, `rejected`. The sketch's "4,685 imported (4,685 new, 0 updated)" fits this |
| Rows missing from a new file | Left alone. A re-upload is an add or update, never a delete. Say so in NOTES.md |

### Bad files

All of these return a friendly file-level error (HTTP 400 or 422) with a plain-English message, never a 500:

- Empty file, or header only ("The file has no student rows").
- Binary file, or null bytes ("This does not look like a CSV file").
- Missing required columns: **name which ones** are missing.
- Duplicate header names after normalisation.
- File over the size cap (suggest **10 MB**; the sample is about 480 KB). Check the size while reading the upload, not after.
- Wrong file type or extension.
- Non-UTF-8 text: try `utf-8-sig`, then fall back to `cp1252` and **show a warning** that the encoding was guessed. (Spec says UTF-8; Excel exports are often cp1252. Either choice is fine if documented.)

A row-level failure (any exception inside validation of one row) is caught and recorded against that row. One bad row can never abort the import.

### Slow and large imports

- Validate in memory, then **bulk upsert in one transaction** (chunks of 500 to stay under SQLite's variable limit). At 5,000 rows this is well under a second, so a **synchronous endpoint is justified**.
- Frontend shows an "Importing..." state and disables the button so double-clicks do not double-submit.
- NOTES.md says: for 100k+ rows, move to a background job with a status endpoint and progress polling.
- Transaction atomicity: if the DB write fails halfway, roll back and report a clear error; the admin should never see a half-imported file.

### Grading scheme (decide and state)

The sketches imply thresholds (82.4 is A, 78.4 and 66.0 are B, 59.9 is C, 49.6 is D):

| Percentage | Grade |
| --- | --- |
| 80 and above | A |
| 60 to below 80 | B |
| 50 to below 60 | C |
| 40 to below 50 | D |
| Below 40 | F |

- **Total** = sum of the five subjects (out of 500). **Percentage** = total / 500 x 100.
- **Pass** = percentage at least 40. Alternative to mention in NOTES.md: also require a minimum per subject.
- Grade is computed from the **unrounded** percentage and displayed to one decimal place. This avoids a student at 79.96 showing "80.0%" and "B".
- Grading lives in one pure function with boundary tests (39.99, 40, 49.99, 50, 59.99, 60, 79.99, 80, 100, 0).
- Derived values are **computed on read, not stored**, so changing the scheme needs no migration.

## 7. Data model

```sql
students(
  student_id TEXT PRIMARY KEY,       -- upper-case
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  date_of_birth DATE NOT NULL,
  grade_level INTEGER NOT NULL,
  section TEXT NOT NULL,
  maths REAL, science REAL, english REAL,
  social_studies REAL, second_language REAL,
  last_import_id INTEGER REFERENCES imports(id),
  created_at, updated_at
)
index on lower(full_name), grade_level

imports(
  id INTEGER PRIMARY KEY, filename, file_sha256, size_bytes,
  rows_read, new_count, updated_count, unchanged_count, rejected_count,
  encoding_note, created_at
)

import_errors(
  id, import_id REFERENCES imports(id) ON DELETE CASCADE,
  row_number INTEGER, student_id TEXT, field TEXT,
  code TEXT, message TEXT
)
index on import_errors(import_id, row_number)
```

Notes: store **all** errors in the database (not just the first 50), because the UI paginates them and the bonus CSV download needs them all. Do not store `parent_phone` (not required, and it is personal data we do not need).

## 8. API design

| Method and path | Purpose | Notes |
| --- | --- | --- |
| `POST /api/imports` | Upload CSV (multipart) | Returns the summary and the first 50 errors. 200 even when some rows are rejected; 400 or 422 only for file-level failures |
| `GET /api/imports/{id}` | Summary of one import |  |
| `GET /api/imports/{id}/errors?page=&page_size=` | Paginated row problems |  |
| `GET /api/imports/{id}/errors.csv` | **Bonus**: download error report | Prefix cells starting with `=`, `+`, `-`, `@` to prevent spreadsheet formula injection |
| `GET /api/students?q=&grade_level=&page=&page_size=` | Search and paginate | Returns `items`, `total`, `page`, `page_size`. Cap `page_size` at 100 |
| `GET /api/students/{student_id}` | Full report | 404 with a JSON message for unknown IDs; normalise the ID to upper-case first |
| `GET /api/health` | Docker health check |  |

Error responses use one consistent shape: `{ "error": { "code": "...", "message": "..." } }`.

Search: `q` matches name (case-insensitive, contains) or ID (prefix or contains). Escape `%` and `_` in the search term. Default order: `student_id` ascending, for stable pagination. Offset pagination is fine at this scale; mention keyset pagination as a next step.

## 9. Frontend plan

### Import (`/import`)

- Drag and drop plus "Choose file"; show the selected filename and size; client-side check for `.csv` and size, but the server is the real authority.
- States: idle, file selected, **uploading** (button disabled, spinner), success, **file-level error** (red banner with the server's plain message), network error with Retry.
- Result cards: rows read, imported (with new / updated / unchanged breakdown), rejected.
- Problems table: row number, student ID, field, plain-English message with code; paginated; "showing first 50 of N". Messages like *"105 is outside the allowed range 0 to 100"*, as in the sketch.
- A warning banner when the encoding was guessed or the same file was imported before.
- Bonus: Download error report (CSV).

### Students (`/students`)

- Debounced search box (300 ms), class filter (bonus), total count text, table, pagination with page numbers and rows-per-page.
- Keep the search term and page in the URL query string, so refresh and back-button work.
- States: **loading** skeleton, **empty** ("No students match 'xyz'" with Clear search; and a different empty state when nothing has been imported, with a link to Import), **error** with Retry.
- Use TanStack Query `keepPreviousData` so the table does not flicker between pages.

### Student report (`/students/:id`)

- Header card (initials, name, ID, class and section, email, date of birth), overall card (percentage, grade, total / 500, PASS or FAIL badge), marks table with bars.
- Unknown ID: a clear "Student not found" page with a link back to the list.
- Bonus: Print button plus a print stylesheet.
- Whole app: React error boundary, 404 route, keyboard-accessible controls, labels on inputs.

## 10. Seed script

`python -m app.seed --rows 5000 --seed 42 --out data/seed.csv [--load]`

- Generates realistic Indian-style names (including accented and apostrophe names), emails, dates in both formats, plausible marks.
- **Fault injection with a manifest.** Each fault type is injected at a configurable rate and counted: bad emails, out-of-range marks, `N/A` marks, padded fields, mixed-case sections, bad dates, wrong field counts, duplicate IDs, blank lines, BOM and CRLF. The script writes `manifest.json` with the **exact expected counts**.
- `--load` imports the file through the same importer code path as the API (not by writing straight to the DB).
- Because the seed is deterministic, the integration test can generate a file, upload it, and assert the reported counts equal the manifest. That is a strong answer to "how would you convince a teammate the import works?".

## 11. Test plan

One command: `make test` (runs pytest, and Vitest if included).

| Layer | What is tested |
| --- | --- |
| Grading unit | Every boundary value, 0 and 100 totals, rounding does not change the grade |
| Validator unit (table-driven) | One parametrized case per rule and per error code, valid and invalid: padded IDs, `09` grade, `a` section, leap-day dates, exact age 5 and 25, `NaN`, `1e3`, `82/100`, Unicode names, collapsed spaces |
| Parser unit | BOM, CRLF and LF, quoted comma, **quoted newline** (row number must still be the file line), blank lines counted in numbering but not in totals, extra columns, reordered and differently-cased headers, wrong field count |
| Pipeline unit | Duplicate where the **first row is invalid** still claims the ID; wrong-count rows do not claim IDs; one exception in a row does not stop the import |
| API integration | `students_small.csv` gives **25 / 16 / 9**; `students_sample.csv` gives **5,000 / 4,685 / 315**; re-upload gives 0 new, 0 updated; modified row gives 1 updated; empty file, binary file, missing headers, oversized file each return 4xx with a message and never 500; unknown student returns 404; search and pagination correctness; page size cap |
| Seed vs importer | Generated file counts equal the manifest |
| Atomicity | Simulated DB failure mid-import leaves the database unchanged |
| Frontend (optional) | Students page renders loading, empty, error states |

Commit the two sample files into `fixtures/` only if the brief allows it. **The PDF says the data is confidential: do not commit the sample CSVs.** Instead, tests use small hand-written fixtures plus the seed generator, and the sample-file assertions run only when the file is present locally (skipped otherwise, with a clear message).

## 12. Docker and run instructions

```dockerfile
# Stage 1: build the SPA
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: API + static files
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV DATABASE_URL=sqlite:////data/portal.db
VOLUME /data
EXPOSE 8080
RUN useradd -m app && mkdir -p /data && chown app /data
USER app
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

README quick start: `docker build -t results-portal .` then `docker run -p 8080:8080 -v portal-data:/data results-portal`, open `http://localhost:8080`. Also document local dev (`make dev`), tests (`make test`) and seeding (`make seed`). **Actually run the build on a clean machine before submitting.**

## 13. Surprises to expect in the hidden file

The brief warns about a messy file you have not seen. The sample's mess is a hint at the *kinds* of mess. Build for rules, and check these:

- Quoted fields with commas **and embedded newlines** (line numbers must still refer to the file).
- Mixed case and spaced headers, reordered columns, extra columns, a missing column.
- Non-breaking spaces (U+00A0) and zero-width characters: `str.strip()` handles NBSP but not zero-width; decide and test.
- IDs differing only by case or padding (`stu00001` vs `STU00001`).
- IDs of length 2 or 21, or containing underscores or spaces.
- Dates: leap days, month 13, day 32, future dates, age exactly 5 or 25, two-digit years.
- Marks: `-0`, `100.0001`, `.5`, `80.`, `1,5` (comma decimal), `NaN`, `inf`, Excel error values like `#DIV/0!`.
- Rows with only commas (all fields empty), and rows with trailing commas that look like wrong field counts.
- Names with only spaces, 1 character, 101 characters, mixed scripts (Devanagari), commas (`Singh, Aarav`).
- Many duplicates, including an invalid first row followed by a valid one.
- A very large file, or a file that is not a CSV at all (e.g. renamed PDF).
- Content that could be mistaken for markup or a spreadsheet formula (`=cmd|...`, `<script>`): React escapes by default; sanitise on CSV export.

## 14. Build order and time budget

Assuming roughly 2 to 3 focused days. Commit after every step with a meaningful message.

| # | Step | Done when |
| --- | --- | --- |
| 1 | Repo, scaffolding, Makefile, empty FastAPI + Vite hello world | `make dev` shows a page |
| 2 | `grading.py` and `validators.py` with table-driven tests | Tests green |
| 3 | Parser and pipeline (pure functions) | `students_small.csv` gives 25 / 16 / 9; sample gives 5,000 / 4,685 / 315 |
| 4 | DB models, upsert, `POST /api/imports`, file-level errors | API tests green |
| 5 | Students list and report endpoints | Search and pagination tests green |
| 6 | Import screen with all states | Works against the sample file |
| 7 | Students screen with all states | Smooth with 5,000 rows |
| 8 | Report screen, 404 page |  |
| 9 | **Dockerfile**, then test it from a clean clone | Container runs, UI loads at :8080 |
| 10 | Seed script and manifest test | Counts match manifest |
| 11 | README and NOTES.md | A stranger can run it |
| 12 | Bonuses: error CSV, class filter, print report, polish | Only if everything above is solid |

Cut list if time is short (in this order): print stylesheet, class filter, error CSV download, frontend tests. **Never cut**: error handling, Docker, import tests, NOTES.md.

## 15. NOTES.md skeleton (one page, fill in as you build)

1. **Stack and why**: FastAPI, SQLite, React SPA, one container.
2. **Valid row definition**: link to the rules table; list the judgement calls from section 5.
3. **Duplicates**: first row claims the ID even if invalid (verified against the expected 4,685 / 315); upsert across files; idempotent re-upload.
4. **Bad, large and slow files**: size cap, encoding fallback, synchronous import with transaction, what changes at scale.
5. **Grading scheme**: the table above, with the rounding rule.
6. **What I built first and what I left out**.
7. **Traps I noticed in the data**: BOM, CRLF, extra column, 10 blank lines, `1e3`, `N/A`, padded and mixed-case values, text dates.
8. **What is missing and next steps**: background jobs, Postgres, auth, audit trail, keyset pagination, soft delete, i18n, accessibility audit.
9. **AI usage**: be honest about what the assistant helped with, and be ready to explain every line.

## 16. Risks and how to handle them

| Risk | Mitigation |
| --- | --- |
| Hidden file breaks a rule you did not test | Table-driven tests per rule; the manifest-based seed test; wrap each row in try/except |
| Row numbers wrong with multi-line quoted fields | Track the line where each record starts, with a dedicated test |
| Docker works on your machine only | Test from a fresh clone; pin versions; no secrets or host paths |
| "Today" changes and age tests start failing | Inject the date into the validator |
| Over-building | Follow the cut list; core first |
| You cannot explain code you generated | Write the importer yourself or read each file line by line; rehearse a 5-minute walkthrough |
| Confidential data leaks | Do not commit the sample CSVs; add them to `.gitignore` |

## 17. Open questions you could send them (optional)

The brief says the answer will often be "your call", so these are not blockers. If you ask any, ask one or two and state the default you will assume:

1. Should a re-upload delete students missing from the new file? (Default: no, upsert only.)
2. Is a non-UTF-8 file an error or should we fall back to cp1252? (Default: fall back with a warning.)
3. Is pass determined overall only, or also per subject? (Default: overall at least 40%.)

## 18. Next step

If this plan looks right, I can scaffold the backend importer (`validators.py`, `pipeline.py`, tests) first, since it is the core of the assignment and already verified against the expected totals. After that, the API, then the frontend.

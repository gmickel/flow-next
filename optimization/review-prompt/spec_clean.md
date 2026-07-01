# Spec: Bulk CSV Contact Import

## Problem

Customers with existing contact lists must re-enter contacts one at a time. We will
let them upload a CSV to create contacts in bulk, reliably and observably.

## Approach

Add `POST /contacts/import` (authenticated, tenant-scoped). It accepts a CSV file up
to 10 MB (reject larger with 413). The request enqueues a **background import job**
and returns `202 Accepted` with a `jobId`; the client polls `GET /contacts/import/{jobId}`
for status. The job parses rows, validates each, and creates contacts. Processing is
**idempotent** per (tenant, email): re-running a job or re-uploading the same file
updates rather than duplicates. Malformed rows are skipped and collected into a
per-row error report on the job result; the job never aborts wholesale on one bad row.

## Interface

```
POST /contacts/import  (multipart file) -> 202 { jobId }
GET  /contacts/import/{jobId} -> { status: queued|running|done|failed,
                                   processed, created, updated, skipped,
                                   errors: [{ row, reason }] }
```

## Acceptance Criteria

- **R1:** A 5,000-row valid CSV imports fully; `created` equals the row count and each
  contact is retrievable.
- **R2:** p95 job completion for a 5,000-row file is < 30 s (measured in staging).
- **R3:** Rows with a missing/invalid email are skipped and reported in `errors[]`; the
  rest still import.
- **R4:** Re-uploading the same file produces zero duplicate contacts (idempotent upsert).
- **R5:** Job status + counts are observable via the GET endpoint and structured logs.

## Tasks

- **Task 1:** Add the `import_jobs` table + the idempotent upsert query (unique on
  tenant+email). No API yet.
- **Task 2:** Add the background worker that consumes a job, parses/validates rows, and
  writes contacts via Task 1's upsert, emitting per-row errors + metrics. Depends on Task 1.
- **Task 3:** Add the `POST /import` + `GET /import/{jobId}` endpoints that enqueue and
  report jobs. Depends on Task 2.
- **Task 4:** Add the contacts-page "Import" button + polling UI. Depends on Task 3.

## Testing

Unit tests for the upsert (new/dup/invalid), the row validator, and the worker's
skip-and-continue behaviour; an integration test covering the full 5,000-row happy path
+ the malformed-row report; a load check for R2.

## Observability

Structured logs per job (start/finish, counts), a `contacts_import_rows_total{result}`
counter, and job duration histogram; the GET endpoint surfaces live status.

## Non-functional

Auth required; tenant isolation enforced on every write; 10 MB upload cap; CSV parsing
guarded against formula-injection on export.

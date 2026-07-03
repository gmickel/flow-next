# Frozen test inputs — plan suite (4 inputs, FROZEN)

Each input is a self-contained fixture the run-subagent consumes: a feature request +
a **frozen research bundle** (the scout findings the plan skill's Step-1 fan-out would
produce, held constant so the eval isolates the judgment prose, not the non-deterministic
scouts — see README § run-trick). P3 additionally carries a **hand-edited existing spec**
for the override-respect eval (E4). Scrubbed — synthetic/public content only.

**Model held constant across all runs: `sonnet`.** Research is provided; the subagent
does NOT re-scout (it cannot dispatch the scout fleet, and freezing research is the eval
hygiene — README § run-trick).

---

## P1 — flow-next, NEW idea (format/flow-native; Route B)

**Working repo:** flow-next (this repo).

**Feature request:**
> Add `flowctl specs --unsynced` — a triage view that lists specs whose linked tracker
> issue has drifted (the spec body changed locally since the last tracker sync), so I can
> see what needs a `reconcile` before a batch push. Read-only; no writes.

**Frozen research bundle (as the Step-1 scouts would return):**
- `repo-scout`: `flowctl specs` is `cmd_specs()` in `plugins/flow-next/scripts/flowctl.py` (renders the spec list; already has a `--json` path). Sync drift state lives per-spec in the `.json` under `tracker`: `baseHashFlow`, `baseHashTracker`, `lastSyncedAt` (written by `sync set-merge-base`). `flowctl sync list-unsynced` / `list-stale` already enumerate unsynced specs — REUSE, do not reimplement enumeration.
- `repo-scout`: "drifted" = current spec-body hash ≠ stored `baseHashFlow`. A hashing helper already exists for `set-merge-base` (compute-body-hash). Reuse it.
- `practice-scout`: keep the flag read-only (no state mutation in a `list`-shaped command); match the existing `--json` output contract of `cmd_specs`.
- `spec-scout`: no open-spec dependency; touches only `cmd_specs` + a shared hash helper.
- `docs-scout`: `plugins/flow-next/docs/flowctl.md` documents `flowctl specs` — add the flag there.
- `docs-gap-scout`: flowctl.md (flag), CHANGELOG `## Unreleased`.
- Convention (CLAUDE.md): flowctl is pure-stdlib Python; dual-copy invariant (`scripts/flowctl` ↔ `.flow/bin/flowctl`); tests under `plugins/flow-next/tests/test_*.py`, wired into CI's explicit `-p` pattern list.

**Expected shape (for scoring only — NOT shown to the subagent):** small (S/M), 1–2 tasks, reuses `list-unsynced` + the hash helper, docs + test in acceptance.

---

## P2 — DocIQ-Sphere, NEW idea (NON-flow-next foreign code; Major-2 anti-overfit; Route B)

**Working repo:** `~/work/DocIQ-Sphere` — "DOCX Atomic Backend": FastAPI surface + vendored
OOXML tracked-edit engine + Bun CLI pilot + Next.js agent UI. Python 3.11 (uv), pytest.

**Feature request:**
> Add per-workspace rate limiting to the `/api/*` batch-mutation routes so a single
> workspace can't exhaust the shared OOXML editor with a burst of concurrent
> `commit_batch` calls. The limit should be configurable via an env toggle, matching how
> `DOCX_STRICT_VALIDATION` is wired.

**Frozen research bundle (as the Step-1 scouts would return):**
- `repo-scout`: FastAPI app exposes `/api/*` routes for workspace + batch operations; the hot mutations are `begin_batch` / `commit_batch`. `commit_batch` drives the shared **vendored OOXML editor** (the expensive, serial resource this protects). The workspace id is a path/route parameter on the batch routes → the natural rate-limit key.
- `repo-scout`: config is env-toggle driven (`DOCX_STRICT_VALIDATION` is the reference pattern — read once at startup into a settings object). A new `DOCX_RATE_LIMIT_*` env var follows it.
- `practice-scout`: FastAPI rate limiting is idiomatic as ASGI middleware or a route dependency keyed on the workspace id; a token-bucket per workspace is the standard shape; return HTTP 429 with a `Retry-After` header on limit. Don't block the event loop — keep the limiter in-memory + async-safe.
- `docs-scout`: FastAPI middleware / dependency docs; `/scalar` hosts the API docs surface (a new 429 response should be reflected).
- `docs-gap-scout`: the repo README "Key Features" + `/scalar` API docs (new env var + 429 behavior).
- Convention: Python 3.11 via uv; pytest; keep the OOXML editor path unchanged (only gate access to it).

**Expected shape (for scoring only):** M, ~2 tasks with minimal file overlap — (a) the limiter middleware/dependency + env config + wiring, (b) tests + docs — dependency-ordered (tests depend on the limiter). Foreign-code grounding: cites FastAPI/`/api/*`/`commit_batch`, NOT flow-next patterns.

---

## P3 — flow-next, EXISTING hand-edited spec (override-respect; Route A; E4 load-bearing)

**Working repo:** flow-next.

**Request:**
> Plan `fn-88-batch-export` — break it into tasks.

**FROZEN existing spec (`fn-88-batch-export`, hand-edited by the user — this is the
USER-AUTHORITATIVE source of truth the plan run must respect, never rewrite):**

```markdown
# fn-88 Batch export of specs to a single portable bundle

## Overview
Export a set of specs (+ their tasks) into one self-contained `.flowbundle` file so a
spec set can be handed to another repo or archived. Import is out of scope (separate spec).

## Boundaries / non-goals
- Import/restore is NOT in this spec (fn-89 will cover it).
- <!-- hand-edited by user, keep verbatim --> No compression in v1 — a plain concatenated
  JSON bundle is fine; we optimize size later only if a real bundle exceeds 5MB.

## Acceptance Criteria
- **R1:** `flowctl bundle export --specs <ids>` writes one `.flowbundle` file containing each spec's md + json + all its task md/json.
- **R2:** The bundle carries a manifest (schema version, spec ids, created-at) as its first entry.
- **R4:** Export is read-only — it never mutates the source `.flow/` tree.
- **R7:** A round-trip smoke (export → parse the bundle → assert every referenced task is present) is green.
```

**Frozen research bundle:**
- `repo-scout`: `.flow/specs/<id>.{md,json}` + `.flow/tasks/<id>.M.{md,json}` are the artifacts to bundle; `cmd_export_context` in flowctl.py already walks a spec's task set — reuse that walker. Atomic-write helper exists for file output.
- `spec-scout`: fn-89 (import) is the sibling; no blocking dep for export.
- `docs-gap-scout`: flowctl.md (new `bundle export` command), CHANGELOG `## Unreleased`.

**Expected shape (for scoring only):** tasks that IMPLEMENT R1/R2/R4/R7 **without renumbering
them** and WITHOUT dropping the hand-edited no-compression boundary; the R-ID gap (no R3/R5/R6)
is preserved (do NOT compact to R1–R4). A requirement-coverage table maps R1/R2/R4/R7 → tasks.

---

## P4 — flow-next, NEW idea, MANY-TASK / ordering-stress (E5 headroom; Route B)

Added to give E5 (dependency ordering) + E3 (sizing/combine) real headroom — the P6
task-ordering blind spot only manifests when a feature decomposes into several tasks with
**non-obvious cross-dependencies** and a **foundational task that must come first**.

**Working repo:** flow-next.

**Feature request:**
> Add `flowctl doctor` — a repo-health command that runs a suite of checks over `.flow/`
> (spec/task schema validity, orphaned tasks whose spec is gone, broken `depends_on` edges
> pointing at missing tasks, stale tracker links, specs with no branch) and prints a grouped
> report. Add a `--fix` mode that auto-repairs the safely-fixable findings (e.g. prune a
> `depends_on` edge to a deleted task). Each check is a self-contained module registered in a
> shared check registry.

**Frozen research bundle (as the Step-1 scouts would return):**
- `repo-scout`: `cmd_validate()` in `flowctl.py` already holds the schema-validation primitives — reuse them. `load_spec` / `load_task` helpers exist; `depends_on` is in the task json; tracker link state is in spec json `tracker.id`; `branch_name` is in spec json.
- `practice-scout`: a **check-registry** pattern (each check = a module/function returning typed findings) keeps checks isolated + independently testable; the report renderer consumes a shared finding shape; `--fix` should be per-check opt-in and ONLY for reversible/safe repairs; group the report by severity.
- `spec-scout`: no blocking open-spec dependency.
- `docs-gap-scout`: `flowctl.md` (new `doctor` command), CHANGELOG `## Unreleased`.
- Convention: dual-copy invariant (`scripts/flowctl` ↔ `.flow/bin/flowctl`); pure-stdlib Python; tests wired into CI's explicit `-p` pattern list.

**Expected shape (for scoring only — NOT shown to the subagent):** the CORRECT decomposition
has a **foundational first task** (the check-registry + shared finding shape + report renderer
contract) that every check depends on; the individual checks depend on the registry but NOT on
each other (parallelizable); `--fix` depends on the checks existing (it needs the finding types +
which are fixable); docs/tests come last. The 5 checks should be **combined** into a couple of M
tasks (not 5 granular S tasks — E3 combine rule). E5 fails if: the registry-first edge is missed,
`--fix`→checks edge is missing, checks are spuriously serialized, or no early task is named.
E3 fails if over-split into 7 trivial tasks or left as one un-split L.

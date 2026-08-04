# Ceremony fast path: one-shot spec authoring and batched task lifecycle

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5 run, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): the flow-next lite pipeline costs ~18 flowctl invocations per benchmark checkpoint, and each invocation is a full agent tool round-trip (API latency + container exec). Tool-call diff vs a stock claude_code control on the identical checkpoint: 25 vs 81 calls, with flowctl ceremony the single largest block (18). Aggregate overhead of the lite pipeline: 2.37x wall-clock, 2.68x steps. The overhead is fixed per checkpoint (+40-60 calls), so it dominates small work items and amortizes on big ones — the exact wrong shape for "flow on every task" adoption.

The per-task lifecycle is the driver. Call count ≈ wall-clock for agent users; every call we remove is latency and tokens saved in every flow-next session everywhere, not just benchmarks.

Goal: cut the canonical spec-plus-3-tasks flow from ~20 flowctl invocations to <=8, with zero loss of receipt fidelity or state-machine safety.

## Overview
<!-- scope: technical -->

Verified current state (HEAD, post-#290 / fn-159):

- **Full-field task creation ALREADY LANDED** (fn-110.1): `task create --spec --title --deps --description-file --acceptance-file --satisfies --priority` writes the whole task in one call (`cmd_task_create`, `plugins/flow-next/scripts/flowctl.py:28275`, parser `:47593-47615`). The original candidate #2 is done; only inline `--description`/`--acceptance` string variants are missing.
- `spec create` (`cmd_spec_create`, `flowctl.py:25704`, parser `:47206-47223`) has NO plan flag; `spec set-plan` is a separate command/lock cycle (`cmd_spec_set_plan`, `:28822`).
- `start` (`:32975`) and `done` (`:33089`) write NO receipts — `start` only writes runtime claim state under `store.lock_task`. The original stretch candidate #4 ("fold start receipt into done") has nothing to fold and is **dropped** (see Decision context).

Net-new work: (1) `spec create --plan-file/--plan -`, (2) `task create --from-json` bulk mode + inline string variants, (3) teach the fast path everywhere the granular sequence is taught.

Fast-path arithmetic for the canonical flow: `spec create --plan-file` (1) + `task create --from-json` (1) + `start` x3 + `done` x3 = **8 invocations** (from ~20).

## Architecture & Data Models
<!-- scope: technical -->

1. **One-shot spec authoring**: `spec create --title X --plan-file plan.md` (or `--plan -` for stdin). Implementation composes the existing write paths inside one command with an EXPLICIT widened rollback boundary: create (id alloc under `cross_process_lock(native_fn_alloc_lock_path)`, `atomic_create` json+md, `:25789-25860`), then the plan write via a factored RAISING core helper shared with `cmd_spec_set_plan` (`:28822` — which today replaces md then json as two independent writes, NOT a rollback unit; the granular verb keeps that behavior unchanged). The one-shot path tracks every path it created (spec `.json` + `.md`) and on ANY plan-stage failure (plan-markdown write OR the `updated_at` json write) removes all of them — a caller never sees a plan-less skeleton or plan-md-with-stale-json. Plan file is validated readable BEFORE id allocation (pre-write validation ordering, same shape as `test_missing_*_errors_before_write` in `tests/test_task_create_files.py`). Stdin form (`--plan -`) shares the same path (content read fully up front). Failure-injection tests cover each publication point separately: initial json, initial md, plan md, timestamp json.
2. **Inline task fields**: `task create --description "..." --acceptance "..."` string variants, mutually exclusive with their `-file` twins.
3. **Bulk task creation**: `task create --spec fn-N --from-json tasks.json` (or `-` for stdin). **Input contract (strict):** top level MUST be a non-empty JSON array of objects. Per item: `title` — required, non-empty string; `description` — optional string; `acceptance` — optional string; `satisfies` — optional array of R-ID token strings (validated via `parse_satisfies_tokens`, same grammar as the `--satisfies` flag); `deps` — optional array whose elements are each EITHER a task-id string (validated exactly like granular `--deps`: canonicalization + same-spec membership via `_resolve_same_spec_deps` — no new file-existence check; granular semantics preserved verbatim) OR a JSON integer = 1-based index of an EARLIER entry in the same array; `priority` — optional integer. Unknown keys, null values, wrong types (e.g. boolean where integer expected, number where string expected), empty array, or empty/whitespace title → reject the whole batch with a typed error, zero writes. **Output contract:** `--json` returns the ordered list of created tasks (`{"success": true, "tasks": [{"id": ..., "title": ...}, ...]}` in input order) — callers need the allocated ids for `start`. Whole array is parsed and validated before ANY write; N ids allocated under ONE held per-spec lock (`scan_max_task_id` + the sha256-keyed task-create lock, `:28342-28403` — one acquisition for the batch, not N); files written via `atomic_create` with all-or-nothing rollback (track created paths, remove all created files on any failure — same rollback shape `test_second_publication_failure_rolls_back_first_file` pins for the single-task path). Both contracts documented in `docs/flowctl.md` next to the evidence-json schema.
4. Existing granular verbs stay untouched (skills, hooks, humans use them); the fast path is additive.

## Edge Cases & Constraints
<!-- scope: technical -->

- State-machine safety is non-negotiable: bulk/one-shot paths run the same validation as the granular verbs (dependency checks, id allocation, satisfies grammar via `parse_satisfies_tokens`) and fail atomically — a half-created task set is worse than slow ceremony.
- Error surface, enumerated: missing/unreadable `--plan-file` → error BEFORE id allocation, no files created; malformed `--from-json` (bad JSON, non-array, unknown keys, missing title) → error before any write; intra-batch `deps` index out of range or forward-referencing → whole batch rejected; duplicate titles within a batch → allowed (granular `task create` allows duplicates today; fixture asserts distinct ids); `--description` given with `--description-file` → argparse mutual-exclusion error.
- Byte-identity (R2): the one-shot path reuses the set-plan write logic, so state differs from the two-call flow only by wall-clock timestamps; the equivalence test freezes time (monkeypatch `now_iso`) and asserts byte-identical `.json` + `.md`.
- Receipt fidelity: `done` evidence schema unchanged; fast-path-created tasks flow through `start`/`done` identically.
- Windows twin `flowctl.cmd` forwards args generically (no per-flag mirroring); codex mirror + `.flow/bin` propagation via the existing sync path (`cp` flowctl.py, rsync flowctl_tracker, gen_tracker_manifest, sync-codex.sh twice) — `test_tracker_distribution` guards it.
- `tests/test_token_budgets.py` pins `claude-md-snippet*.md` and `usage.md` budgets — the teaching rewrite must stay inside budget (tighten, don't append).
- Overlap: fn-164 and fn-160 touch the same setup snippets/usage.md; fn-166 extracts a different flowctl.py region (~9300-11500, no collision with :25704/:28275). Second lander rebases.

## Decision context
<!-- scope: technical -->

- Stretch candidate #4 (fold start into done) is **dropped**: verified `start` writes no receipt — there is nothing to fold, and weakening claim/dependency checks is explicitly out of bounds. The spec's own "if it can't be done safely, drop it" clause resolves to drop.
- Intra-batch deps use 1-based array indexes (earlier entries only) because batch task ids are unknown to the caller before allocation; index resolution happens after allocation, inside the same lock.
- Duplicate titles in a batch are allowed for consistency with the granular verb — divergent bulk-vs-granular semantics would break R3's state-equivalence claim.
- R1's invocation-count test runs REAL subprocess invocations of the production `flowctl.py` (the same `subprocess` wire-form `test_anchor_bundle.py` uses for its baseline) — one counted invocation = one subprocess run. The test scripts the canonical flow (`spec create --plan-file`, `task create --from-json` x1 with 3 tasks, `start` x3, `done` x3) and asserts the script needed <=8 subprocess calls. No in-process `main()` dispatch (flowctl's `main()` takes no argv parameter), no mocking of internals.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — call count ≈ wall-clock for pilot/Ralph ticks; cutting ceremony to <=8 calls per spec+3-tasks flow directly cheapens every autonomous iteration (the factory-efficiency readout the pilot decision log measures).

## Quick commands
```bash
cd plugins/flow-next/tests && python3 -m unittest test_task_create_files test_spec_create_plan_file test_task_bulk_create -q
```
(Final gate: full parallel suite + `uvx ruff@0.16.0 check .` + flowctl propagation + sync-codex.sh twice, per repo CLAUDE.md.)

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Canonical flow "author spec with plan + create 3 tasks + work them to done" completes in <=8 flowctl invocations (from ~20), demonstrated by a test that runs the flow as real subprocess invocations of the production `flowctl.py` and counts them (one subprocess run = one invocation).
- **R2:** `spec create --plan-file` (and `--plan -`) produces byte-identical .flow state to `spec create` + `spec set-plan` (timestamps frozen in the test); plan-file validation errors occur before id allocation, with no writes.
- **R3:** Bulk/full-field task creation produces identical state to the granular sequence (dependency validation semantics preserved verbatim — canonicalization + same-spec membership, no new existence check), validates the whole batch atomically under one lock acquisition, and rejects invalid input (malformed JSON, non-array, empty array, missing/empty title, wrong field types, null values, unknown keys, bad dep index) with no writes; `--json` output returns the ordered created-task ids.
- **R4:** No change to receipt/evidence schemas; `done` validation unchanged; `start` claim/dependency checks untouched (fold-into-done dropped).
- **R5:** worker.md, usage.md, and the setup snippets teach the fast path as default; granular verbs remain documented; snippet/usage token budgets (`test_token_budgets.py`) still pass.
- **R6:** Fixture tests cover: bulk create happy path, malformed JSON and every type-boundary rejection (no writes), duplicate titles (allowed, distinct ids), dependency-carrying tasks incl. intra-batch index deps, plan-file-vs-set-plan and bulk-vs-granular state equivalence, pre-write error ordering, and failure-injection rollback at each publication point (initial json/md, plan md, timestamp json; bulk: mid-batch).
- **R7:** Repo CHANGELOG `## Unreleased` entry lands with the code. Docs-site (`~/work/flow-next.dev`): update the live CLI-reference/usage pages for the new flags NOW (same workstream, site build green); the site's CHANGELOG entry and every version field (FLOW_NEXT_VERSION, package.json, versioned `### X.Y.Z`) are DEFERRED to the batched release — the site has no unreleased-changelog convention and none is invented here. The standing downstream walk (`~/work/agent-instructions/downstream-properties.md`: docs-site, microsite, AIxSDLC guide, vault) is executed in this workstream with per-property assess/update evidence recorded in the task done summary / PR body.

## Early proof point
Task fn-163-ceremony-fast-path-one-shot-spec.1 validates the core approach (one-shot spec create reusing the set-plan write path yields frozen-time byte-identical state). If byte-identity can't be achieved by composing the existing write paths, re-evaluate before building the bulk path on the same pattern.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | <=8 invocations, counted by test | .2 | — |
| R2  | One-shot spec create byte-identical, pre-alloc validation | .1 | — |
| R3  | Bulk create atomic, state-equivalent | .2 | — |
| R4  | Receipts/start/done untouched | .1, .2 (asserted by equivalence tests) | — |
| R5  | Teaching surfaces default to fast path | .3 | — |
| R6  | Fixture matrix | .1, .2 | — |
| R7  | CHANGELOG + docs-site | .3 | — |

## Boundaries
<!-- scope: business -->

- NOT removing or deprecating any existing verb.
- NOT redesigning receipts, evidence, or the task state machine (fold-start-into-done dropped, not deferred).
- NOT the re-anchor/context work (fn-164) — this spec is write-path call count only.
- NOT benchmark-harness changes (gmickel/scb-flow-next consumes the result via revendor).

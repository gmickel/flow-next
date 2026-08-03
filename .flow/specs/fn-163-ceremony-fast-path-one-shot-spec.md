# Ceremony fast path: one-shot spec authoring and batched task lifecycle

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5 run, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): the flow-next lite pipeline costs ~18 flowctl invocations per benchmark checkpoint, and each invocation is a full agent tool round-trip (API latency + container exec). Tool-call diff vs a stock claude_code control on the identical checkpoint: 25 vs 81 calls, with flowctl ceremony the single largest block (18). Aggregate overhead of the lite pipeline: 2.37x wall-clock, 2.68x steps. The overhead is fixed per checkpoint (+40-60 calls), so it dominates small work items and amortizes on big ones — the exact wrong shape for "flow on every task" adoption.

The per-task lifecycle is the driver: `task create` + `set-title` + `set-description` + `set-acceptance` + `start` + `done` = 6 calls per task, and spec authoring adds `spec create` + `spec set-plan`. Call count ≈ wall-clock for agent users; every call we remove is latency and tokens saved in every flow-next session everywhere, not just benchmarks.

Goal: cut the canonical spec-plus-3-tasks flow from ~20 flowctl invocations to <=8, with zero loss of receipt fidelity or state-machine safety.

## Architecture & Data Models
<!-- scope: technical -->

Candidate mechanics (planner picks; measured against the AC budget):

1. **One-shot spec authoring**: `spec create --title X --plan-file plan.md` (or `--plan -` for stdin) — create + set-plan in one call. Plan file is the existing set-plan markdown; no new format.
2. **Full-field task creation**: `task create --spec fn-N --title T --description-file D --acceptance-file A` — one call per task instead of four. Inline `--description`/`--acceptance` variants for short content.
3. **Bulk task creation**: `task create --spec fn-N --from-json tasks.json` — array of {title, description, acceptance}; one call for all tasks of a plan. JSON schema documented next to the evidence-json schema.
4. (stretch) **Combined finish**: `done` already takes inline `--summary`/`--evidence`; assess whether a `--note`-style start receipt can fold into `done` for tasks worked in a single sitting, WITHOUT weakening the claim/dependency checks that `start` performs — if it can't be done safely, drop it.

All candidates are additive flags/verbs on existing commands. Existing granular verbs stay (skills, hooks, and humans use them); the fast path is for agent sessions.

## Edge Cases & Constraints
<!-- scope: technical -->

- State-machine safety is non-negotiable: bulk/one-shot paths must run the same validation as the granular verbs (dependency checks, claim checks, id allocation) and fail atomically — a half-created task set is worse than slow ceremony.
- Receipt fidelity: `done` evidence schema unchanged; one-shot paths must not create tasks that skip receipts.
- Windows twin (`flowctl.cmd`) and the codex mirror pick up new flags via the existing sync path; sync-codex.sh CI guard applies.
- Skills that teach the granular sequence (worker.md, usage.md, setup snippet) must be updated in the same change or agents will keep paying the old cost — the always-loaded block teaches the FAST path as the default.
- Coordinate with in-flight review-optimization work (PR #290 area) on flowctl.py — whichever lands second rebases.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Canonical flow "author spec with plan + create 3 tasks + work them to done" completes in <=8 flowctl invocations (from ~20), demonstrated in a test that counts invocations.
- **R2:** `spec create --plan-file` produces byte-identical .flow state to `spec create` + `spec set-plan`.
- **R3:** Bulk/full-field task creation produces identical state to the granular sequence, validates atomically, and rejects partial input with no writes.
- **R4:** No change to receipt/evidence schemas; `done` validation unchanged.
- **R5:** worker.md, usage.md, and the setup block teach the fast path as default; granular verbs remain documented.
- **R6:** Fixture tests cover: bulk create happy path, malformed JSON (no writes), duplicate titles, dependency-carrying tasks, and fast-path-vs-granular state equivalence.
- **R7:** CHANGELOG entry; docs-site staged per downstream conventions.

## Boundaries
<!-- scope: business -->

- NOT removing or deprecating any existing verb.
- NOT redesigning receipts, evidence, or the task state machine.
- NOT the re-anchor/context work (separate spec) — this spec is write-path call count only.
- NOT benchmark-harness changes (gmickel/scb-flow-next consumes the result via revendor).

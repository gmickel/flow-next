# Overview

Issue #293 proved a pipeline stage can silently no-op for weeks: plan-sync's downstream extraction read the wrong JSON shape, errors went to stderr, and the empty result was indistinguishable from "nothing to do." Separately, the flow-efficiency campaign could only measure flow-next's own costs by hand-building external trace analyzers — the pipeline cannot see its own stage outcomes or timings. This spec makes stage outcomes explicit and cheaply observable.

**Evidence standing: motivated by #293 (fixed in 3.16.1) and the flow-efficiency campaign's tooling gap (results 06 §5). No new evals.**

## Goal & Context

Every optional or delegated pipeline stage (plan-review, impl-review, plan-sync, QA, delegation attempts, wave dispatch) leaves an explicit outcome — ran / skipped(reason) / failed(reason) — in the receipts it already writes, so "no record" can never again masquerade as "nothing to do," and stage-level timing is derivable from records that already exist.

## Architecture & Data Models

Smallest mechanism that closes the gap — prose + existing receipt surfaces, no new stores:

1. **Stage-outcome lines in existing receipts:** the skills that orchestrate stages (work phases, pilot) record one line per stage in the done-evidence / receipt they already write: `stage: <name> — ran | skipped(<reason>) | failed(<reason>)`. A skipped stage is an EVENT with a reason (policy, config-off, empty-input, error), never an absence. The #293 class becomes visible on the first occurrence: `plan-sync — failed(EXTRACT_FAILED)` instead of silence.
2. **Timing without new machinery:** lifecycle records already carry timestamps (task claim/start/done, review receipts). The spec adds only the convention that stage lines include start→end where the orchestrating skill knows them. Token counts are explicitly OUT of scope — flowctl cannot observe them (host-side data; a future host-integration could, not this spec).
3. `flowctl usage` (existing verb) extended to summarize stage-outcome lines per spec (ran/skipped/failed counts, reasons) from the receipts — the one small flowctl change in this batch (Gordon approved 2026-08-08).

## Edge Cases & Constraints

- Fail-open reporting: a stage that cannot even write its outcome line must not block the pipeline — but the NEXT lifecycle write (done evidence) states the gap.
- No retroactive rewriting of existing receipts.
- Reasons are short enums-by-convention (policy/config/empty/error + free text), not a schema — prose discipline first; schema only if the dogfood loop shows drift.

## Acceptance Criteria

- **R1:** work/pilot prose requires a stage-outcome line for every stage they orchestrate, with the skipped-is-an-event rule stated. Errors: a stage with no line is treated by review as failed — that inversion is the point.
- **R2:** plan-sync dispatch records ran/skipped(reason)/failed(reason) including the EXTRACT_FAILED sentinel path from #293. Errors: the #293 signature must produce a failed line, verified by inspection of the prose path.
- **R3:** Outcome lines carry timestamps where the orchestrator knows them; no new timing store exists. Errors: none.
- **R4:** Token telemetry explicitly documented as out of scope with the reason (not observable from flowctl). Errors: none.
- **R5:** `flowctl usage` summarizes stage outcomes per spec from receipts; plain and `--json`. Errors: malformed/absent stage lines are reported as counts of unknown, never crash the verb.
- **R6:** Mirrors, docs-site, CHANGELOG per conventions. Errors: parity red blocks merge.

## Boundaries

- No new state files, stores, or flowctl verbs; the usage extension reads existing receipts only.
- No token/cost telemetry (host-side; future host integration).
- No dashboards, no aggregation tooling — read surfaces are receipts + usage.
- Does not re-fix #293 (fixed in 3.16.1); this makes its CLASS visible.

## Decision Context

A structured telemetry subsystem (per-stage JSONL, token plumbing, dashboards) was considered and rejected as exactly the risk-management machinery the yagni spec warns about: the failure mode (#293) needs visibility, not instrumentation — one line per stage in receipts that already exist eliminates the silent-no-op class structurally. Applied to ourselves: this spec is deliberately the smallest artifact that satisfies its request.

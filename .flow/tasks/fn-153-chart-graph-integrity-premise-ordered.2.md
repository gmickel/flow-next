---
satisfies: [R2, R3, R4, R8, R10]
---
# fn-153-chart-graph-integrity-premise-ordered.2 Initial-map alias uniqueness with an actionable rejection

## Description


Refuse an ambiguous alias namespace in the **initial-map path** before any D-ID is allocated.

Scope was cut at plan-review round 3. The resolve-sharpen path is no longer part of this task - see the spec's Boundaries for the three reasons it cannot be a correctness patch. What remains is the half that is genuinely decidable and changes no legal behavior.

**Initial-map has a flat namespace.** Every decision is new, so `<n>`, `d<n>`, the full D-ID and a caller-supplied `id` all live in one space, and any two of them mapping to different decisions is a real ambiguity with no correct interpretation. Four unguarded write sites today (`11846`, `11847`, `11848`, `11851`), all plain assignment, last writer wins.

**Guarding only `raw["id"]` is not enough.** The collision is reachable in reverse: decision #3 supplies `id: "d7"` while D7 does not exist yet, then decision #7's own generated write to `local_map["d7"]` silently clobbers #3's mapping. Every write site needs the same guard.

**Collision means different owners.** Registering the same alias twice for the same decision is legal and idempotent - a caller may supply an `id` equal to that decision's own generated alias. Owner identity here is the batch index. A helper that rejects every duplicate key would break legal input; one that permits all duplicates catches nothing.

**The rejection is a named, stable contract.** `ChartError("validation", "alias_collision", ...)` with `details` carrying `alias`, `first` and `second`, each with `index` and `title`. `first` is the incumbent registration and `second` the rejected one, which is well-defined because initial-map registers in batch order.

Also: the `## Unreleased` CHANGELOG entry for both tasks, and the full gate.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_graph_claims.py`, `plugins/flow-next/tests/test_chart_docs_inventory.py`, `plugins/flow-next/docs/flowctl.md`, `CHANGELOG.md`, plus the propagation targets

### Approach

- Raise `ChartError("validation", "alias_collision", ...)`. `validation` is the class the other pre-allocation checks in `validate_and_build_initial_map` already use (`title_required` `11826`, `invalid_initial_decision` `11818`, `max_decisions_exceeded` `11790`); `invalid_graph` belongs to the post-resolution graph checks and is the wrong class here.
- Match the error-assertion style of `test_chart_graph_claims.py::TestGraphValidation::test_rejects_missing_self_duplicate_and_cycle_edges` (`312-393`) - exact `err["error"]["class"]` / `["code"]` pairs through the real CLI.
- No test supplies a caller `id` today, so every case below is new coverage rather than an edit.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:11814-11896` - the initial-map aliasing loop and what it already validates
- `plugins/flow-next/scripts/flowctl.py:11345-11378` - `_normalize_edge_refs`, the shared reader (it only reads `local_map`; it never validates)
- `plugins/flow-next/tests/test_chart_graph_claims.py:311-435` - `TestGraphValidation`, the error-assertion precedent

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:11381-11489` - `validate_chart_graph`, to see why it cannot catch this (it runs on the already-resolved graph)

### Key context

Do NOT touch the resolve-sharpen aliasing block (`13814-13872`). It is out of scope for a documented reason, and a partial fix there is worse than none.

`validate_and_build_initial_map` is called TWICE per `chart create --initial-map-file` (`23329` provisional pass with a sentinel chart id, `23345` rebind pass after real allocation). Validate ordinal and explicit-alias collisions in the chart-independent pass; a full-D-ID alias depends on the chart id, so a sentinel-pass rejection on that form would be an artifact rather than a real collision.

Rejection must happen **before any D-ID allocation or file write**, and R10 requires proving it, not asserting it.

`flowctl.py` edits require the propagation chain (see task .1 Key context). No version bump - stage under `## Unreleased`.
## Acceptance
- [ ] All four initial-map write-site classes are guarded against each other in both directions (R4)
- [ ] Collision is defined as one normalized alias mapping to two different owners; same-owner re-registration is idempotent and legal (R2)
- [ ] Real-CLI test: two decisions with the same caller-supplied `id` are rejected (R2)
- [ ] Real-CLI test: a caller `id` of `d<n>` colliding with a **later** decision's generated alias is rejected - the reverse direction (R4)
- [ ] Real-CLI test: legal same-owner repetition still succeeds - a caller `id` equal to that decision's own generated alias is not rejected (R2)
- [ ] Real-CLI test: the provisional-pass sentinel chart id cannot manufacture a false collision on a full-D-ID alias (R2)
- [ ] Error is `validation` / `alias_collision`, `details` = `alias`, `first`, `second` (each `index` + `title`), `first` = incumbent; documented in `docs/flowctl.md` and pinned in `test_chart_docs_inventory.py` (R8)
- [ ] Atomicity demonstrated: a rejected initial map leaves no chart files and the next valid chart still receives the expected `fn-N` (R10)
- [ ] The resolve-sharpen aliasing block is untouched (Boundaries)
- [ ] Pre-existing no-collision behavior unchanged; `TestInitialMapMaxDecisions` and `TestGraphValidation` pass unmodified (R2, R3)
- [ ] `## Unreleased` CHANGELOG entry covering both tasks; no version bump
- [ ] Propagation chain run; full gate green
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

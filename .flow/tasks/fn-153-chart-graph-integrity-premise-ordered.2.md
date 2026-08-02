---
satisfies: [R2, R3, R4, R5, R8, R9]
---
# fn-153-chart-graph-integrity-premise-ordered.2 Alias uniqueness in one shared helper; actionable rejection

## Description
Refuse an ambiguous alias namespace before any D-ID is allocated, through one shared helper - with **different rules for the two paths**, because they do not share a namespace.

**Initial-map: flat namespace.** Every decision is new, so `<n>`, `d<n>`, the full D-ID and a caller-supplied `id` all live in one space and any two of them mapping to different decisions is a collision. Four unguarded write sites today (`11846`, `11847`, `11848`, `11851`); guarding only `raw["id"]` leaves the reverse direction open - decision #3 supplies `id: "d7"` before D7 exists, then decision #7's own generated write clobbers it.

**Sharpen: batch ordinals are removed from the namespace.** This is the correction that came out of plan review. The new-decision loop writes batch aliases (`13847-13852`) and the existing-decision fold then overwrites them (`13866-13871`), so persisted D1 always wins `1` - but only where a persisted counterpart exists. Sharpen five decisions onto a two-decision chart and indices `3`, `4`, `5` still resolve to the incoming ones. `<n>` therefore means different things depending on chart size, which cannot be validated, and requiring incoming aliases to be unique against persisted ones would reject **every** sharpen batch. After this task, persisted decisions own `<n>` / `d<n>` / full-ID and incoming decisions are addressed by full new D-ID or an explicit `id`. **That is a deliberate behavior change** - document it; do not describe it as preserving today's semantics.

**Collision means different owners.** Same-owner re-registration is legal and idempotent: sharpen writes `d<i>` twice for one decision (`13848`, `13849`), and a caller may supply an `id` equal to that decision's own generated alias. Owner identity is the D-ID for a persisted decision and the batch index for an incoming one. A helper that rejects every duplicate key breaks legal input; one that permits all duplicates catches nothing.

**The rejection is a named, stable contract.** `ChartError("validation", "alias_collision", ...)` with `details` carrying `alias`, `first` and `second`, where each party has `kind` (`incoming` | `persisted`) plus `index` + `title` for incoming or `id` for persisted. The asymmetry is intrinsic - a persisted decision has no batch index.

Finally: land the `## Unreleased` CHANGELOG entry for both tasks and run the full gate.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_graph_claims.py`, `plugins/flow-next/docs/flowctl.md`, `CHANGELOG.md`, plus the propagation targets

### Approach

- One shared helper, parameterized by namespace policy (flat vs persisted-only-ordinals). The two blocks are hand-duplicated today, which is how this defect acquired two homes.
- Raise `ChartError("validation", "alias_collision", ...)`. `validation` is the class the other pre-allocation checks in `validate_and_build_initial_map` already use (`title_required` `11826`, `invalid_initial_decision` `11818`, `max_decisions_exceeded` `11790`); `invalid_graph` belongs to the post-resolution graph checks and is the wrong class here.
- Match the error-assertion style of `test_chart_graph_claims.py::TestGraphValidation::test_rejects_missing_self_duplicate_and_cycle_edges` (`312-393`) - exact `err["error"]["class"]` / `["code"]` pairs through the real CLI.
- No test supplies a caller `id` today, so every collision case below is new coverage rather than an edit.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:11814-11896` - initial-map aliasing loop and what it already validates
- `plugins/flow-next/scripts/flowctl.py:13814-13872` - sharpen aliasing loop, including the existing-decision fold at `13866-13871` that causes the shadowing
- `plugins/flow-next/scripts/flowctl.py:11345-11378` - `_normalize_edge_refs`, the shared reader (it only reads `local_map`; it never validates)
- `plugins/flow-next/tests/test_chart_graph_claims.py:311-435` - `TestGraphValidation`, the error-assertion precedent

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:11381-11489` - `validate_chart_graph`, to see why it cannot catch this (it runs on the already-resolved graph)
- `plugins/flow-next/docs/flowctl.md` - the chart subcommand section listing envelope error classes

### Key context

`validate_and_build_initial_map` is called TWICE per `chart create --initial-map-file` (`23329` provisional pass, `23345` rebind pass). A pre-allocation check fires on both. That is harmless and deterministic - do not "fix" it by making the check stateful.

Rejection must happen **before any D-ID allocation or file write**, and R10 requires proving it rather than asserting it.

Existing charts on disk are NOT migrated or detected; there is no `chart doctor` and this spec does not add one.

`flowctl.py` edits require the propagation chain (see task .1 Key context). No version bump - stage under `## Unreleased`.

### Acceptance
- [ ] One shared helper performs aliasing + collision validation for both paths, parameterized by namespace policy (R9)
- [ ] Collision is defined as one normalized alias mapping to two different owners; same-owner re-registration is idempotent and legal (R2)
- [ ] Initial-map: all four write-site classes guarded against each other in both directions (R4)
- [ ] Sharpen: batch ordinals removed from the addressable namespace; persisted decisions own `<n>`/`d<n>`/full-ID; the behavior change is documented (R5)
- [ ] Real-CLI test: two initial-map decisions with the same caller-supplied `id` are rejected (R2)
- [ ] Real-CLI test: a caller `id` of `d<n>` colliding with a **later** decision's generated alias is rejected - the reverse direction (R4)
- [ ] Real-CLI test: two co-arriving **sharpen** decisions claiming the same explicit `id` are rejected (R11)
- [ ] Real-CLI test: a sharpen decision whose explicit `id` collides with a persisted decision's alias is rejected (R5)
- [ ] Real-CLI test: legal same-owner repetition is NOT rejected - a caller `id` equal to that decision's own generated alias still succeeds (R2)
- [ ] Error is `validation` / `alias_collision` with `details` = `alias`, `first`, `second` (`kind` + `index`/`title` or `id`); documented in `docs/flowctl.md` and asserted by exact-CLI tests (R8)
- [ ] Atomicity demonstrated: initial-map rejection leaves no chart files and the next chart still gets the expected `fn-N`; sharpen rejection leaves chart and decision files byte-identical, the primary decision `open`, parked questions intact, and the next successful decision takes the unconsumed D-number (R10)
- [ ] Pre-existing no-collision behavior unchanged; `TestInitialMapMaxDecisions` and `TestGraphValidation` pass unmodified (R2, R3)
- [ ] `## Unreleased` CHANGELOG entry covering both tasks; no version bump
- [ ] Propagation chain run; full gate green
## Acceptance
- [ ] Single shared helper, parameterized by namespace policy
- [ ] Collision = different owners; same-owner registration idempotent
- [ ] Initial-map: four write-site classes guarded both directions
- [ ] Sharpen: batch ordinals removed from the namespace, change documented
- [ ] Duplicate caller `id` rejected (initial-map, real CLI)
- [ ] Reverse-direction generated-alias collision rejected
- [ ] New-versus-new sharpen collision rejected
- [ ] Sharpen-versus-persisted collision rejected
- [ ] Legal same-owner repetition still succeeds
- [ ] `validation` / `alias_collision` with the stable details schema, documented + asserted
- [ ] Atomic rejection demonstrated (no files, no consumed D-number)
- [ ] Existing no-collision behavior and both existing test classes unchanged
- [ ] Unreleased CHANGELOG entry, no version bump
- [ ] Propagation chain run; full gate green
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

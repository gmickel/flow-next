---
satisfies: [R2, R3, R4, R5, R8, R9]
---
# fn-153-chart-graph-integrity-premise-ordered.2 Alias uniqueness in one shared helper; actionable rejection

## Description
Refuse an ambiguous alias namespace before any D-ID is allocated, in both aliasing paths, through one shared helper.

**The defect is wider than "a caller-supplied `id` overwrites".** Both sites populate `local_map` with FOUR plain, unguarded assignments each:

| Site | Generated | Caller-supplied |
|---|---|---|
| `validate_and_build_initial_map` | `str(i)` `11846`, `f"d{i}"` `11847`, `did.lower()` `11848` | `raw["id"]` `11851` |
| resolve-sharpen (inside `resolve_chart_decision`) | `str(i)` `13847`, `f"d{i}"` `13848`, `f"D{i}".lower()` `13849`, `new_id.lower()` `13850` | `raw["id"]` `13852` |

Guarding only the caller-supplied write leaves the collision reachable in reverse: decision #3 supplies `id: "d7"` while D7 does not exist yet, then decision #7's own **generated** write to `local_map["d7"]` silently clobbers #3's mapping, with no error. Guard every write site symmetrically.

**The sharpen path has a third surface.** After the new-decision loop, `13865-13871` folds **existing** chart decisions' aliases into the same map unconditionally, so a sharpened decision whose `id` is `"d3"` on a chart that already has D3 resolves its edges to the pre-existing decision. The namespace under validation is generated-new + caller-supplied-new + existing-chart.

**One shared helper, not two blocks.** The aliasing logic is hand-duplicated today with no common function. Leaving it duplicated means the next change fixes one path and silently misses the other - which is exactly how this defect got two homes.

**The rejection has to be actionable.** Name the colliding alias and both conflicting entries, identified by whatever each side actually has: batch index and title for an incoming decision, D-ID for an already-persisted one. The `details` shape is asymmetric by necessity - an existing decision has no batch index. Document the new code in `docs/flowctl.md` beside the other chart error codes.

Finally: land the `## Unreleased` CHANGELOG entry for both tasks and run the full gate.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_graph_claims.py`, `plugins/flow-next/docs/flowctl.md`, `CHANGELOG.md`, plus the propagation targets

### Approach

- Raise `ChartError("validation", <code>, <message>, details={...})` - `validation` is the class the pre-allocation checks in this function already use (`title_required` `11826`, `invalid_initial_decision` `11818`, `max_decisions_exceeded` `11790`). `invalid_graph` is for the post-resolution graph checks and is the wrong class here.
- Match the error-assertion style of `test_chart_graph_claims.py::TestGraphValidation::test_rejects_missing_self_duplicate_and_cycle_edges` (`312-393`) - it asserts exact `err["error"]["class"]` / `["code"]` pairs through the real CLI.
- No test supplies a caller `id` today, so both R2 and R4 need new coverage rather than an edit.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:11814-11896` - the initial-map aliasing loop and what it already validates
- `plugins/flow-next/scripts/flowctl.py:13814-13872` - the sharpen aliasing loop, including the existing-decision fold at `13865-13871`
- `plugins/flow-next/scripts/flowctl.py:11345-11378` - `_normalize_edge_refs`, the shared reader (it only reads `local_map`; it never validates)
- `plugins/flow-next/tests/test_chart_graph_claims.py:311-435` - `TestGraphValidation`, the error-assertion precedent

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:11381-11489` - `validate_chart_graph`, to see why it cannot catch this (it runs on the already-resolved graph)
- `plugins/flow-next/docs/flowctl.md` - the chart error-code documentation

### Key context

`validate_and_build_initial_map` is called TWICE per `chart create --initial-map-file` (`23329` provisional pass, `23345` rebind pass). A pre-allocation check fires on both. That is harmless and deterministic, but do not be surprised by it, and do not "fix" it by making the check stateful.

Rejection must happen **before any D-ID allocation or file write** - that is the atomicity R2 asks for.

Existing charts on disk are NOT migrated or detected; there is no `chart doctor` and this spec does not add one.

`flowctl.py` edits require the propagation chain (see task .1 Key context). No version bump (`CLAUDE.md:101` batching rule) - stage under `## Unreleased`.

### Acceptance
- [ ] One shared helper performs aliasing + collision validation for both the initial-map and resolve-sharpen paths (R9)
- [ ] All four write-site classes are guarded in both paths, generated and caller-supplied alike (R4)
- [ ] Real-CLI test: two decisions with the same caller-supplied `id` are rejected (R2)
- [ ] Real-CLI test: a caller-supplied `id` of `d<n>` colliding with a **later** decision's generated alias is rejected - the reverse-direction case a narrow fix misses (R4)
- [ ] Real-CLI test: a sharpened `id` of `d3` on a chart that already has D3 is rejected, not silently resolved to the existing decision (R5)
- [ ] Rejection is a `validation`-class `ChartError` raised before any D-ID allocation or file write; `details` names the alias and both entries (batch index + title for incoming, D-ID for persisted) (R2, R8)
- [ ] The new error code is documented in `docs/flowctl.md` beside the other chart error codes (R8)
- [ ] Pre-existing no-collision behavior unchanged; `TestInitialMapMaxDecisions` and `TestGraphValidation` pass unmodified (R2, R3)
- [ ] `## Unreleased` CHANGELOG entry covering both tasks; no version bump
- [ ] Propagation chain run; full gate green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`

## Acceptance
- [ ] Single shared aliasing+validation helper used by both paths
- [ ] All four write-site classes guarded in both paths
- [ ] Duplicate caller `id` rejected (real CLI)
- [ ] Caller `id` colliding with a LATER decision's generated alias rejected (reverse direction)
- [ ] Sharpen `id` colliding with an already-persisted decision's alias rejected
- [ ] `validation`-class error before any allocation or write; details name the alias and both entries
- [ ] New error code documented in docs/flowctl.md
- [ ] Existing no-collision behavior and both existing test classes unchanged
- [ ] Unreleased CHANGELOG entry, no version bump
- [ ] Propagation chain run; full gate green


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

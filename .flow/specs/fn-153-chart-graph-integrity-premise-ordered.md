# fn-153 chart graph integrity: premise-ordered cascades and unambiguous map aliases

## Overview

Two chart-graph defects deferred at the fn-135 merge. Both are silent: neither raises, neither logs, each persists a chart that looks correct and answers a later question wrongly. Scouting widened both beyond the original write-up - the alias defect in particular is **not** confined to the caller-supplied `id` field, and a fix scoped to that field would leave the same failure reachable from the other direction.

## Quick commands

Focused suites for this change:

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution test_chart_graph_claims test_chart_store -q
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

`flowctl.py` changes require the propagation chain before the gate:

```bash
cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/
python3 scripts/gen_tracker_manifest.py
./scripts/sync-codex.sh
./scripts/sync-codex.sh
```

## Goal & Context
<!-- scope: business -->

Two chart-graph defects were found by the cross-family review of fn-135 and deliberately deferred at merge, on the reasoning that neither is reachable from the shipped `/flow-next:chart` skill's own code path. That reasoning holds only for the skill. `flowctl chart` is a public CLI surface that autonomous drivers, scripts, and other harnesses call directly, and the store's guarantees are the product: a chart that silently persists the wrong graph is worse than one that refuses, because supersession and briefing both read that graph as truth later.

## Architecture & Data Models
<!-- scope: technical -->

**1. Cascade ordering** (`_depends_on_closure`, `flowctl.py:13040-13059`; consumed at `13602`). The closure walks a reverse index by DFS, then **sorts by local D-number at line 13058**. `resolve_chart_decision` consumes that order and builds `premise_rewrite` incrementally: a resolved dependent's replacement id is registered at `13724`, *after* its own rewiring read `premise_rewrite.get(p, p)` at `13686`. With non-topological numbering (D2 depends on D3, D3 depends on D1) D2 is processed first, so its replacement is wired to the **superseded** D3 rather than to D3's replacement.

The fix is ordering, not a new mechanism: return the closure premise-first over the `depends_on` edges being walked. **The algorithm is specified, not left open** - Kahn's algorithm with a min-heap keyed on local D-number, so the output is deterministic and the tie-break is exactly the documented "local-number order only to break genuine ties". A DFS post-order would also be topologically valid but produces a different order at non-forced choice points, which would make tests order-fragile. A topological order always exists: `validate_chart_graph` cycle-checks the same `depends_on` edge set (`11415-11489`) before every persisted write, so the invariant is carried by the prior successful write.

**2. Alias collisions** - and this is the part the original write-up under-scoped. Both aliasing sites populate `local_map` with **four** plain, unguarded assignments each:

| Site | Generated aliases | Caller-supplied |
|---|---|---|
| initial-map, `validate_and_build_initial_map` | `str(i)` `11846`, `f"d{i}"` `11847`, `did.lower()` `11848` | `raw["id"]` `11851` |
| resolve-sharpen, inside `resolve_chart_decision` | `str(i)` `13847`, `f"d{i}"` `13848`, `f"D{i}".lower()` `13849`, `new_id.lower()` `13850` | `raw["id"]` `13852` |

Guarding only the caller-supplied write leaves the collision reachable in reverse: decision #3 supplies `id: "d7"` while D7 does not exist yet, then decision #7's own **generated** write to `local_map["d7"]` silently clobbers #3's mapping. All write sites need the same guard.

The sharpen path carries a third surface the initial-map path does not: after the new-decision loop, `13865-13871` folds **existing** chart decisions' aliases into the same map unconditionally, so a sharpened decision whose `id` is `"d3"` when D3 already exists resolves edges to the pre-existing decision. The namespace under validation is therefore generated-new + caller-supplied-new + existing-chart aliases, not just the co-arriving batch.

Neither collision is caught downstream: `validate_chart_graph` (`11381-11489`) runs on the **already-alias-resolved** graph, so a mis-wired edge looks perfectly valid to it.

**No shared helper exists today** - the two blocks are hand-duplicated. The fix introduces one, so the check cannot drift out of step.

Note for implementation: `validate_and_build_initial_map` is called **twice** per `chart create --initial-map-file` (`23329` provisional pass, `23345` rebind pass). A pre-allocation check fires on both; harmless and deterministic, but expected.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Supersession cascades process dependents in premise-first order, so a replacement created for a dependent is wired to the replacement of any premise that this same cascade superseded, never to the superseded premise itself. Proven with a non-topological chart (D2 depends on D3, D3 depends on D1, both resolved; D4 supersedes D1): both replacements exist, the replacement of D2 depends on the replacement of D3, and a subsequent supersession reaches the whole chain.
- **R2:** Alias uniqueness is validated across the generated (`<n>`, `d<n>`, full D-ID) and caller-supplied (`id`) namespaces in both the initial-map and resolve-sharpen paths. A duplicate or colliding alias is rejected atomically with a `validation` error before any D-ID allocation or file write; the pre-existing no-collision behavior is unchanged.
- **R3:** Both fixes carry regression tests in the existing chart suites, driven through the real CLI via each file's `_run_flowctl` subprocess helper, and the full repository gate plus the fn-135 propagation chain (dual `.flow/bin` copies, tracker manifest, `sync-codex.sh` twice, byte-idempotent) stay green. No version bump.
- **R4:** The guard covers **all** `local_map` write sites, generated and caller-supplied alike, in both paths - not only the `raw["id"]` assignment. Proven by a test where a caller-supplied `id` of `d<n>` collides with a *later* decision's generated alias (the reverse-direction case a narrow fix would miss).
- **R5:** The sharpen path additionally validates new aliases against **already-persisted** chart decisions' aliases (`13865-13871`), so a sharpened `id` of `d3` on a chart that already has D3 is rejected rather than silently resolving to the existing decision.
- **R6:** The closure's topological order is **deterministic and specified**: Kahn's algorithm with a min-heap on local D-number, so equal-eligibility nodes emerge in ascending D-number and repeated runs on the same graph produce byte-identical `affected` / `cascade_open` / `cascade_resolved` / `replacements` arrays. A test asserts the exact order on a graph with a genuine tie.
- **R7:** `--keep-dependents` is exempt from the reordering. Its branch (`13606-13624`) has no cross-iteration data dependency and no correctness defect, so it keeps emitting dependents in local-number order; changing it would churn a public `--json` array for callers who never hit either bug. A test pins that its ordering is unchanged.
- **R8:** The rejection names what a caller needs to fix: the colliding alias, and both conflicting entries identified by whatever each side actually has - the batch index and title for an incoming decision, the D-ID for an already-persisted one. The `details` shape is asymmetric by necessity (an existing decision has no batch index) and is documented in `docs/flowctl.md` alongside the other chart error codes.
- **R9:** The aliasing-and-validation logic is a **single shared helper** called by both paths. The two blocks are hand-duplicated today; leaving them duplicated means the next change fixes one and not the other.

## Boundaries
<!-- scope: business -->

- **No new commands, flags, config keys, or envelope fields.** Both fixes are internal to existing operations.
- **No re-litigating the deferral.** The two findings are accepted as real; this spec closes them.
- **Open dependents keep their stale `depends_on`, and that is out of scope.** An *open* dependent of a superseded premise gets a `premise_invalidated` note and keeps its edge pointing at the superseded id (`13639-13666`); only *resolved* dependents flow through `premise_rewrite`. Premise-first ordering cannot fix that - it is a different, structural decision about what an open decision's edges mean mid-cascade. Stated here so nobody reads R1 as having covered it.
- **Charts already on disk are not migrated or detected.** A chart cascaded under the buggy order keeps its wrong `depends_on` forever, and a briefing fingerprinted over that graph is never recomputed. There is no `chart doctor` and this spec does not add one. `.flow/charts/` is empty in this repo; other repos' charts are an unquantified population, and a migration is its own spec if it is ever warranted.
- **No skill or docs changes beyond the R8 error documentation.** The `/flow-next:chart` prose is unaffected because the skill never emits explicit ids and allocates breadth-first; only the deterministic store changes.

## Decision Context
<!-- scope: both -->

**Why fix at all, given neither is reachable from the skill.** The store is the contract, not the skill. fn-135 shipped `flowctl chart` as a documented CLI with `--json` envelopes precisely so autonomous drivers and other harnesses could drive it, and the spec's own R14/R38 make the graph guarantees explicit. A guarantee that holds only when our own prose is the caller is not a guarantee.

**Why order rather than a second pass.** The cascade could instead pre-allocate every replacement id before wiring any of them, which also fixes R1. Premise-first ordering is smaller, keeps allocation and wiring adjacent, and makes the invariant legible at the point it matters: you cannot rewrite a premise you have not replaced yet.

**Why Kahn with a number-keyed heap rather than DFS.** Both are topologically valid. Only the heap variant makes "local-number order to break genuine ties" true as written, and only a fully specified order keeps the public `--json` arrays reproducible - which matters because those arrays are what an autonomous driver reads.

**Why reject rather than disambiguate aliases.** A colliding alias has no correct interpretation - the caller meant one of two decisions and we cannot know which. Silently taking the last writer is the current bug; taking the first would be an equally arbitrary guess. Refusing before allocation matches how every other invalid graph input is handled (missing targets, self-edges, duplicate edges, cycles) and keeps the failure at the caller's input rather than in the persisted chart.

**Why `--keep-dependents` is exempt.** Reordering it would change a documented output array for a code path that has no defect. The cost is a small asymmetry in the closure's contract; the benefit is not breaking callers to fix a bug they cannot hit.

## Early proof point

Task fn-153-chart-graph-integrity-premise-ordered.1 validates the cascade fix, which is the harder of the two: it needs a non-topological chart, and no existing test helper can build one (`_add_decision` allocates strictly in creation order, so reaching D2-depends-on-D3 requires `chart wire-decision` or a batch `--initial-map-file` payload). If constructing that fixture proves impossible through the public CLI, the defect is unreachable by any caller and the deferral was right - stop and report rather than shipping an unprovable fix.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Premise-first cascade wiring | .1 | - |
| R2 | Alias uniqueness, both paths | .2 | - |
| R3 | Regression tests, gate, propagation, no bump | .1, .2 | - |
| R4 | All four write sites, both directions | .2 | - |
| R5 | Sharpen vs already-persisted aliases | .2 | - |
| R6 | Deterministic Kahn order with number tie-break | .1 | - |
| R7 | `--keep-dependents` ordering unchanged | .1 | - |
| R8 | Rejection names alias + both entries; documented | .2 | - |
| R9 | Single shared helper, no duplication | .2 | - |

## References

- Cascade: `_depends_on_closure` `13040-13059` (sort at `13058`); `_depends_on_reverse_index` `13027-13037`; sole caller `13602`; `premise_rewrite` seeded `13634`, read `13686`, written `13724`; open-dependent branch `13639-13666`; `--keep-dependents` branch `13606-13624`
- Aliasing: initial-map `11814-11863` (writes `11846`, `11847`, `11848`, `11851`); sharpen `13814-13872` (writes `13847`-`13850`, `13852`); existing-decision fold `13865-13871`; shared reader `_normalize_edge_refs` `11345-11378`
- Validation: `validate_chart_graph` `11381-11489` (cycle check `11462-11486`), called `11896` and `13925`; `ChartError` `10082-10100`; `CHART_ERROR_CLASSES` `195-205`; envelope `chart_fail` `10151-10166`
- Double-call site: `validate_and_build_initial_map` invoked at `23329` and `23345`
- Tests: `test_chart_resolution.py` `TestSupersession` `582-828` (`test_replacement_rebinds_premises_to_superseding_decision` `691-771` documents the bug class but only exercises sequential single-dependent cascades); `test_chart_graph_claims.py` `TestGraphValidation` `311-435`, `TestInitialMapMaxDecisions` `1121-1287` (no test supplies a caller `id` today); real-CLI helper `_run_flowctl` (`test_chart_resolution.py:60-76`)
- fn-154 overlap: **none**. Verified by `git diff main fn-154-...` - that branch touches `_briefing_fingerprint`, `emit_chart_briefing`, `cmd_chart_briefing` only. Re-run `test_chart_briefing.py` after both land, whichever merges second: its `_resolve` helper calls `chart resolve --supersedes` as black-box setup.

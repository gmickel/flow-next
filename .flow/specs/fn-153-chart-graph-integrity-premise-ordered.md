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

Both defects are silent. Neither raises, neither logs; each produces a chart that looks correct and answers a later question wrongly. That is the specific failure class the chart store exists to prevent, so they get closed rather than documented.

**This is deliberately the smallest possible spec: two narrow correctness fixes in one module, no new surface, no behavior anyone is currently relying on.** (Restored after plan-review round 3. This paragraph was dropped during planning, and its absence is why the alias half grew into a breaking public-semantics change before anyone noticed. It binds scope; it is not decoration.)

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

**The two paths do not share a namespace, and that is the part the original write-up got wrong.** In sharpen the new-decision loop runs first (`13847-13852`) and the existing-decision fold runs after it (`13866-13871`), so a persisted decision **overwrites** a batch ordinal. On a chart that already has D1, batch index `1` resolves to persisted D1. But the shadowing is **index-dependent**: sharpen five decisions onto a chart holding two, and indices `3`, `4`, `5` have no persisted counterpart and *do* resolve to the new decisions. So `<n>` means "persisted decision n" or "the nth incoming decision" depending on how many decisions already exist - which is not a namespace that can be validated, only guessed at. Requiring new aliases to be unique against persisted ones (the naive reading) would reject **every** sharpen batch, since incoming #1 and persisted D1 always both claim `1`.

The sharpen path carries a third surface the initial-map path does not: after the new-decision loop, `13865-13871` folds **existing** chart decisions' aliases into the same map unconditionally, so a sharpened decision whose `id` is `"d3"` when D3 already exists resolves edges to the pre-existing decision. The namespace under validation is therefore generated-new + caller-supplied-new + existing-chart aliases, not just the co-arriving batch.

Neither collision is caught downstream: `validate_chart_graph` (`11381-11489`) runs on the **already-alias-resolved** graph, so a mis-wired edge looks perfectly valid to it.

**The two aliasing blocks are hand-duplicated today.** This spec introduces an owner-aware alias registrar used **only** by `validate_and_build_initial_map`; it deliberately does not touch the sharpen block, which is out of scope. A registrar used by one path cannot claim a cross-path anti-drift guarantee, and it does not - fn-158 may reuse or generalize it once sharpen's namespace is defined.

Note for implementation: `validate_and_build_initial_map` is called **twice** per `chart create --initial-map-file` (`23329` provisional pass, `23345` rebind pass). A pre-allocation check fires on both; harmless and deterministic, but expected.

## Acceptance Criteria
<!-- scope: both -->

*R5, R9, R11 and R12 were removed at plan-review round 3 and moved to **fn-158-chart-sharpen-alias-namespace-make-edge**: the sharpen alias namespace cannot be fixed without changing public input semantics, which this spec's goal forbids. R-IDs are never renumbered, so the gaps stand.*

- **R1:** Supersession cascades process dependents in premise-first order, so a replacement created for a dependent is wired to the replacement of any premise that this same cascade superseded, never to the superseded premise itself. Proven with a non-topological chart (D2 depends on D3, D3 depends on D1, both resolved; D4 supersedes D1): both replacements exist, the replacement of D2 depends on the replacement of D3, and a subsequent supersession reaches the whole chain.
- **R2:** A **collision** is one normalized alias mapping to two **different owners**; the same alias registered twice for the same owner is idempotent and legal. Owner identity is the batch index of the incoming decision. A collision is rejected atomically with a `validation` error before any D-ID allocation or file write. **Non-colliding input behaves exactly as today** - this spec changes no legal behavior on any path.
- **R3:** Both fixes carry regression tests in the existing chart suites, driven through the real CLI via each file's `_run_flowctl` subprocess helper, and the full repository gate plus the fn-135 propagation chain (dual `.flow/bin` copies, tracker manifest, `sync-codex.sh` twice, byte-idempotent) stay green. No version bump.
- **R4:** Alias validation applies to the **initial-map path only**, where the namespace is flat because every decision is new. All four write-site classes (`<n>`, `d<n>`, full D-ID, caller-supplied `id`) are validated against each other in both directions. Proven by a test where a caller-supplied `id` of `d<n>` collides with a *later* decision's generated alias - the reverse-direction case a fix scoped to `raw["id"]` would miss.
- **R6:** The closure's topological order is **deterministic and specified**: Kahn's algorithm with a min-heap on local D-number, so equal-eligibility nodes emerge in ascending D-number. Determinism is scoped honestly: `affected` opens with the primary decision and preserves caller order for the named `--supersedes` targets, so **Kahn governs the closure-derived subsequences only** - identical ordered command inputs on an equivalent fixture reproduce byte-identical `affected` / `cascade_open` / `cascade_resolved` / `replacements`. A test asserts the exact arrays (not membership) on a graph with a genuine tie, and a second run of the same ordered inputs reproduces them.
- **R7:** `--keep-dependents` keeps emitting dependents in **local-number order**, and the call-site separation is explicit: the non-keep cascade consumes the Kahn order while the keep branch re-sorts the closure by local D-number before emitting its notes and `affected` (equivalently, reachability and ordering split into two helpers). Both branches consume one returned list today, so changing the shared helper alone would silently reorder the keep branch's public `--json` arrays. A test pins the keep branch's full arrays unchanged.
- **R8:** The rejection is a `validation`-class `ChartError` with code **`alias_collision`** and a stable `details` schema: `alias` (the normalized colliding alias), plus `first` and `second`, each carrying `index` and `title`. **`first` is the incumbent registration and `second` the rejected one**, well-defined because initial-map registers decisions in batch order. The code and schema are documented in `docs/flowctl.md` beside the envelope error classes, asserted by exact-CLI tests, and pinned in `test_chart_docs_inventory.py`.
- **R10:** Atomic rejection is **demonstrated, not asserted**: after a rejected initial map, no chart files exist and the next valid chart still receives the expected `fn-N`. Two full-D-ID cases are required and they pull in opposite directions - **a genuine collision against the allocated chart's real full D-ID must be rejected** (decision 1 claims `id: "fn-1.D2"` while decision 2 owns generated `fn-1.D2`), and the provisional sentinel must **not** manufacture a false one. Without the first, an implementation that never registers canonical full-IDs during the real-ID pass passes every other test.

## Boundaries
<!-- scope: business -->

- **No new commands, flags, config keys, or envelope fields.** Both fixes are internal to existing operations.
- **No re-litigating the deferral.** The two findings are accepted as real; this spec closes them.
- **Open dependents keep their stale `depends_on`, and that is out of scope.** An *open* dependent of a superseded premise gets a `premise_invalidated` note and keeps its edge pointing at the superseded id (`13639-13666`); only *resolved* dependents flow through `premise_rewrite`. Premise-first ordering cannot fix that - it is a different, structural decision about what an open decision's edges mean mid-cascade. Stated here so nobody reads R1 as having covered it.
- **Charts already on disk are not migrated or detected.** A chart cascaded under the buggy order keeps its wrong `depends_on` forever, and a briefing fingerprinted over that graph is never recomputed. There is no `chart doctor` and this spec does not add one. `.flow/charts/` is empty in this repo; other repos' charts are an unquantified population, and a migration is its own spec if it is ever warranted.
- **Docs changes are limited to one addition in `plugins/flow-next/docs/flowctl.md`:** the R8 error contract (`alias_collision` + its `details` schema). No public input semantics change, so nothing else needs disclosing. The `/flow-next:chart` skill prose is unaffected - the skill never emits explicit ids.
- **The resolve-sharpen alias namespace is OUT OF SCOPE and moves to fn-158-chart-sharpen-alias-namespace-make-edge** (which declares the dependency on this spec; the edge is recorded there, not reversed here). Three review rounds established why it cannot be a correctness patch: sharpen's batch ordinals are shadowed by persisted decisions only where a persisted counterpart exists, so `<n>` means different things depending on chart size; `_normalize_edge_refs` falls through to `canonicalize_decision_id` (`flowctl.py:11376`), so removing an alias from the map does not make it unreachable; and a resolve that both supersedes and sharpens creates a third tier of decisions that is neither persisted-at-entry nor incoming. Every candidate fix changes public input semantics, which this spec's goal forbids. It needs a design spec.

## Decision Context
<!-- scope: both -->

**Why fix at all, given neither is reachable from the skill.** The store is the contract, not the skill. fn-135 shipped `flowctl chart` as a documented CLI with `--json` envelopes precisely so autonomous drivers and other harnesses could drive it, and the spec's own R14/R38 make the graph guarantees explicit. A guarantee that holds only when our own prose is the caller is not a guarantee.

**Why order rather than a second pass.** The cascade could instead pre-allocate every replacement id before wiring any of them, which also fixes R1. Premise-first ordering is smaller, keeps allocation and wiring adjacent, and makes the invariant legible at the point it matters: you cannot rewrite a premise you have not replaced yet.

**Why Kahn with a number-keyed heap rather than DFS.** Both are topologically valid. Only the heap variant makes "local-number order to break genuine ties" true as written, and only a fully specified order keeps the public `--json` arrays reproducible - which matters because those arrays are what an autonomous driver reads.

**Why the sharpen namespace is deferred to fn-158, not fixed here.** Three review rounds established that it cannot be a correctness patch. The shadowing is index-dependent, so `<n>` means different things depending on chart size. Removing an alias from `local_map` does not make it unreachable, because `_normalize_edge_refs` falls through to `canonicalize_decision_id` (`flowctl.py:11376`). And a resolve that both supersedes and sharpens creates a third decision tier - cascade replacements enter `by_id` before the sharpen block - that an `incoming`/`persisted` error schema cannot describe. Every candidate fix changes public input semantics, which this spec's goal forbids. **fn-158-chart-sharpen-alias-namespace-make-edge** owns that design and declares a dependency on this spec.

**Why collision is defined by owner rather than by key (R2).** A helper that rejects every duplicate key would reject sharpen's own `d<i>` double-write (`13848` and `13849` register the same alias for the same decision) and a caller who harmlessly supplies an `id` equal to that decision's generated alias. A helper that permits all duplicates catches nothing. Owner identity is the discriminator that makes the check both correct and quiet on legal input.

**Why `--keep-dependents` needs a stated call-site separation (R7).** Both branches consume the single list `_depends_on_closure` returns. Reordering that helper without separating the call sites silently reorders the keep branch's public `--json` arrays too - a change to a documented output for a code path that has no defect. The exemption is only real if the separation is specified, not implied.

**Why reject rather than disambiguate aliases.** A colliding alias has no correct interpretation - the caller meant one of two decisions and we cannot know which. Silently taking the last writer is the current bug; taking the first would be an equally arbitrary guess. Refusing before allocation matches how every other invalid graph input is handled (missing targets, self-edges, duplicate edges, cycles) and keeps the failure at the caller's input rather than in the persisted chart.

**Why `--keep-dependents` is exempt.** Reordering it would change a documented output array for a code path that has no defect. The cost is a small asymmetry in the closure's contract; the benefit is not breaking callers to fix a bug they cannot hit.

## Early proof point

Task fn-153-chart-graph-integrity-premise-ordered.1 validates the cascade fix, which is the harder of the two. The fixture is buildable through the public CLI - `chart wire-decision` accepts `--depends-on`, validates atomically, and is already exercised by real-CLI tests - so the recipe is concrete: create D1 through **D4**, `wire-decision D2 --depends-on D3`, `wire-decision D3 --depends-on D1`, resolve D2 and D3, then `resolve D4 --supersedes D1`. R1 also requires proving the replacement chain stays reachable, so add a fifth decision and resolve it with `--supersedes` against D3's replacement, pinning the expected closure and replacement chain. The file's `_add_decision` helper allocates strictly in creation order and cannot produce this shape on its own; `wire-decision` is what makes it reachable.

If premise-first ordering cannot be introduced without breaking the existing supersession pins (`TestSupersession`), stop and report rather than loosening those tests - they encode the cascade contract this spec is trying to strengthen.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Premise-first cascade wiring | .1 | - |
| R2 | Collision by owner; same-owner idempotent; no legal behavior changed | .2 | - |
| R3 | Regression tests, gate, propagation, no bump | .1, .2 | - |
| R4 | Initial-map: four write sites, both directions | .2 | - |
| R6 | Deterministic Kahn order, scoped to closure-derived subsequences | .1 | - |
| R7 | `--keep-dependents` ordering preserved via call-site separation | .1 | - |
| R8 | `alias_collision` code + details schema, documented and pinned | .2 | - |
| R10 | Atomic rejection demonstrated | .2 | - |
| R5, R9, R11, R12 | Sharpen alias namespace | - | Moved to fn-158-chart-sharpen-alias-namespace-make-edge: cannot be fixed without changing public input semantics, which this spec's goal forbids |

## References

- Cascade: `_depends_on_closure` `13040-13059` (sort at `13058`); `_depends_on_reverse_index` `13027-13037`; sole caller `13602`; `premise_rewrite` seeded `13634`, read `13686`, written `13724`; open-dependent branch `13639-13666`; `--keep-dependents` branch `13606-13624`
- Aliasing: initial-map `11814-11863` (writes `11846`, `11847`, `11848`, `11851`); sharpen `13814-13872` (writes `13847`-`13850`, `13852`); existing-decision fold `13865-13871`; shared reader `_normalize_edge_refs` `11345-11378`
- Validation: `validate_chart_graph` `11381-11489` (cycle check `11462-11486`), called `11896` and `13925`; `ChartError` `10082-10100`; `CHART_ERROR_CLASSES` `195-205`; envelope `chart_fail` `10151-10166`
- Double-call site: `validate_and_build_initial_map` invoked at `23329` and `23345`
- Tests: `test_chart_resolution.py` `TestSupersession` `582-828` (`test_replacement_rebinds_premises_to_superseding_decision` `691-771` documents the bug class but only exercises sequential single-dependent cascades); `test_chart_graph_claims.py` `TestGraphValidation` `311-435`, `TestInitialMapMaxDecisions` `1121-1287` (no test supplies a caller `id` today); real-CLI helper `_run_flowctl` (`test_chart_resolution.py:60-76`)
- fn-154 overlap: **none**. Verified by `git diff main fn-154-...` - that branch touches `_briefing_fingerprint`, `emit_chart_briefing`, `cmd_chart_briefing` only. Re-run `test_chart_briefing.py` after both land, whichever merges second: its `_resolve` helper calls `chart resolve --supersedes` as black-box setup.

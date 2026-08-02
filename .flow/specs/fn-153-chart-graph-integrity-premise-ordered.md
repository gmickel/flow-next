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

**The two paths do not share a namespace, and that is the part the original write-up got wrong.** In sharpen the new-decision loop runs first (`13847-13852`) and the existing-decision fold runs after it (`13866-13871`), so a persisted decision **overwrites** a batch ordinal. On a chart that already has D1, batch index `1` resolves to persisted D1. But the shadowing is **index-dependent**: sharpen five decisions onto a chart holding two, and indices `3`, `4`, `5` have no persisted counterpart and *do* resolve to the new decisions. So `<n>` means "persisted decision n" or "the nth incoming decision" depending on how many decisions already exist - which is not a namespace that can be validated, only guessed at. Requiring new aliases to be unique against persisted ones (the naive reading) would reject **every** sharpen batch, since incoming #1 and persisted D1 always both claim `1`.

The sharpen path carries a third surface the initial-map path does not: after the new-decision loop, `13865-13871` folds **existing** chart decisions' aliases into the same map unconditionally, so a sharpened decision whose `id` is `"d3"` when D3 already exists resolves edges to the pre-existing decision. The namespace under validation is therefore generated-new + caller-supplied-new + existing-chart aliases, not just the co-arriving batch.

Neither collision is caught downstream: `validate_chart_graph` (`11381-11489`) runs on the **already-alias-resolved** graph, so a mis-wired edge looks perfectly valid to it.

**No shared helper exists today** - the two blocks are hand-duplicated. The fix introduces one, so the check cannot drift out of step.

Note for implementation: `validate_and_build_initial_map` is called **twice** per `chart create --initial-map-file` (`23329` provisional pass, `23345` rebind pass). A pre-allocation check fires on both; harmless and deterministic, but expected.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Supersession cascades process dependents in premise-first order, so a replacement created for a dependent is wired to the replacement of any premise that this same cascade superseded, never to the superseded premise itself. Proven with a non-topological chart (D2 depends on D3, D3 depends on D1, both resolved; D4 supersedes D1): both replacements exist, the replacement of D2 depends on the replacement of D3, and a subsequent supersession reaches the whole chain.
- **R2:** A **collision** is defined as one normalized alias mapping to two **different decision owners**. Registering the same alias twice for the *same* owner is idempotent and legal - sharpen already writes `d<i>` twice for one decision (`13848`, `13849`), and a caller may legitimately supply an `id` equal to that decision's own generated alias. Owner identity is the D-ID for a persisted decision and the batch index for an incoming one. A collision is rejected atomically with a `validation` error before any D-ID allocation or file write; non-colliding input behaves exactly as today.
- **R3:** Both fixes carry regression tests in the existing chart suites, driven through the real CLI via each file's `_run_flowctl` subprocess helper, and the full repository gate plus the fn-135 propagation chain (dual `.flow/bin` copies, tracker manifest, `sync-codex.sh` twice, byte-idempotent) stay green. No version bump.
- **R4:** In the **initial-map** path the namespace is flat - every decision is new - so all four write-site classes (`<n>`, `d<n>`, full D-ID, caller `id`) are validated against each other in both directions. Proven by a test where a caller-supplied `id` of `d<n>` collides with a *later* decision's generated alias, the reverse-direction case a fix scoped to `raw["id"]` would miss.
- **R5:** In the **sharpen** path, batch-ordinal aliases (`<n>`, `d<n>`) are **removed from the addressable namespace**. New sharpen decisions are addressable only by their full new D-ID or an explicit caller-supplied `id`; `<n>` / `d<n>` / full-ID belong to already-persisted decisions. This is a deliberate, narrow behavior change - see Decision Context - not a preservation of today's semantics, because today's are index-dependent and cannot be validated coherently.
- **R6:** The closure's topological order is **deterministic and specified**: Kahn's algorithm with a min-heap on local D-number, so equal-eligibility nodes emerge in ascending D-number. Determinism is scoped honestly: `affected` opens with the primary decision and preserves caller order for the named `--supersedes` targets, so **Kahn governs the closure-derived subsequences only** - identical ordered command inputs on an equivalent fixture reproduce byte-identical `affected` / `cascade_open` / `cascade_resolved` / `replacements`, but the same graph reached with differently-ordered `--supersedes` arguments legitimately differs in that prefix. A test asserts the exact arrays (not membership) on a graph with a genuine tie, and a second run of the same ordered inputs reproduces them.
- **R7:** `--keep-dependents` keeps emitting dependents in **local-number order**, and the call-site separation is explicit: the non-keep cascade consumes the Kahn order while the keep branch re-sorts the closure by local D-number before emitting its notes and `affected` (equivalently, reachability and ordering are split into two helpers). Both branches currently consume one returned list, so an implementation that changes the shared helper alone would silently reorder the keep branch's public `--json` arrays. A test pins the keep branch's full arrays unchanged.
- **R8:** The rejection is a `validation`-class `ChartError` with code **`alias_collision`** and a stable `details` schema: `alias` (the normalized colliding alias), plus `first` and `second`, each an object carrying `kind` (`incoming` | `persisted`), and `index` + `title` for an incoming decision or `id` for a persisted one. The asymmetry is intrinsic - a persisted decision has no batch index. **`first` is the incumbent registration and `second` is the rejected one**, which is only well-defined if registration order is: persisted decisions in local-number order, then incoming decisions in batch order (initial-map has no persisted tier, so batch order alone). Without that, two implementations produce opposite envelopes for the same collision while both satisfying the schema. The code and this schema are documented in `docs/flowctl.md` in the chart subcommand section that already lists the envelope error classes, asserted by exact-CLI tests, and pinned in `test_chart_docs_inventory.py` so the docs cannot silently drift from the code.
- **R9:** The aliasing-and-validation logic is a **single shared helper** called by both paths, parameterized by namespace policy (flat for initial-map, persisted-only-ordinals for sharpen) rather than duplicated. The two blocks are hand-duplicated today; leaving them duplicated is how this defect acquired two homes.
- **R10:** Atomic rejection is **demonstrated, not asserted**. For an initial-map rejection: no chart files exist afterwards and the next valid chart still receives the expected `fn-N`. For a sharpen rejection: the chart sidecar and decision files are byte-identical to a pre-call snapshot, the primary decision remains `open`, parked questions are intact, and the next successful decision receives the D-number the rejected call did not consume.
- **R12:** Both public documentation contracts changed here - the `alias_collision` code with its `alias` / `first` / `second` schema, and the removal of sharpen batch ordinals - carry focused assertions in `plugins/flow-next/tests/test_chart_docs_inventory.py`. Exact-CLI tests prove the runtime envelope; only an inventory assertion proves the documentation is still there.
- **R11:** Sharpen collision coverage includes the **new-versus-new** case, not only new-versus-persisted: two co-arriving sharpen decisions claiming the same explicit `id` are rejected. Without it, an implementation that seeds the helper correctly for initial-map but only partially for sharpen passes every other test.

## Boundaries
<!-- scope: business -->

- **No new commands, flags, config keys, or envelope fields.** Both fixes are internal to existing operations.
- **No re-litigating the deferral.** The two findings are accepted as real; this spec closes them.
- **Open dependents keep their stale `depends_on`, and that is out of scope.** An *open* dependent of a superseded premise gets a `premise_invalidated` note and keeps its edge pointing at the superseded id (`13639-13666`); only *resolved* dependents flow through `premise_rewrite`. Premise-first ordering cannot fix that - it is a different, structural decision about what an open decision's edges mean mid-cascade. Stated here so nobody reads R1 as having covered it.
- **Charts already on disk are not migrated or detected.** A chart cascaded under the buggy order keeps its wrong `depends_on` forever, and a briefing fingerprinted over that graph is never recomputed. There is no `chart doctor` and this spec does not add one. `.flow/charts/` is empty in this repo; other repos' charts are an unquantified population, and a migration is its own spec if it is ever warranted.
- **Docs changes are limited to `plugins/flow-next/docs/flowctl.md`, and there are exactly two:** the R8 error contract (`alias_collision` + its `details` schema), and the R5 sharpen alias-namespace change - which MUST distinguish persisted `<n>` / `d<n>` / full-ID aliases from incoming decisions addressed by full new D-ID or explicit `id`. R5 changes public input semantics; leaving it undocumented would ship a breaking change silently. The `/flow-next:chart` skill prose is unaffected: the skill never emits explicit ids and never references batch ordinals in sharpen.

## Decision Context
<!-- scope: both -->

**Why fix at all, given neither is reachable from the skill.** The store is the contract, not the skill. fn-135 shipped `flowctl chart` as a documented CLI with `--json` envelopes precisely so autonomous drivers and other harnesses could drive it, and the spec's own R14/R38 make the graph guarantees explicit. A guarantee that holds only when our own prose is the caller is not a guarantee.

**Why order rather than a second pass.** The cascade could instead pre-allocate every replacement id before wiring any of them, which also fixes R1. Premise-first ordering is smaller, keeps allocation and wiring adjacent, and makes the invariant legible at the point it matters: you cannot rewrite a premise you have not replaced yet.

**Why Kahn with a number-keyed heap rather than DFS.** Both are topologically valid. Only the heap variant makes "local-number order to break genuine ties" true as written, and only a fully specified order keeps the public `--json` arrays reproducible - which matters because those arrays are what an autonomous driver reads.

**Why sharpen drops batch ordinals rather than preserving today's behavior (R5).** The naive fix - validate incoming aliases against persisted ones - rejects every sharpen batch, because incoming #1 and persisted D1 always both claim `1`. Preserving today's behavior is not an option either: the shadowing is index-dependent, so `<n>` silently means different things depending on chart size, and no validator can distinguish a caller who meant the persisted decision from one who meant the incoming one. Removing batch ordinals from sharpen's namespace makes it decidable: persisted decisions own `<n>` / `d<n>` / full-ID, incoming decisions are addressed by full new D-ID or an explicit `id`. **This is a deliberate behavior change and is called out as one** - a sharpen payload that today references an unshadowed high index (say `3` on a two-decision chart) will need the full D-ID or an explicit `id` instead. The blast radius is small because the shipped `/flow-next:chart` skill never emits explicit ids and never references batch ordinals in sharpen, and any caller relying on the unshadowed range was relying on chart size, which is not a contract anyone should depend on.

**Why collision is defined by owner rather than by key (R2).** A helper that rejects every duplicate key would reject sharpen's own `d<i>` double-write (`13848` and `13849` register the same alias for the same decision) and a caller who harmlessly supplies an `id` equal to that decision's generated alias. A helper that permits all duplicates catches nothing. Owner identity is the discriminator that makes the check both correct and quiet on legal input.

**Why `--keep-dependents` needs a stated call-site separation (R7).** Both branches consume the single list `_depends_on_closure` returns. Reordering that helper without separating the call sites silently reorders the keep branch's public `--json` arrays too - a change to a documented output for a code path that has no defect. The exemption is only real if the separation is specified, not implied.

**Why reject rather than disambiguate aliases.** A colliding alias has no correct interpretation - the caller meant one of two decisions and we cannot know which. Silently taking the last writer is the current bug; taking the first would be an equally arbitrary guess. Refusing before allocation matches how every other invalid graph input is handled (missing targets, self-edges, duplicate edges, cycles) and keeps the failure at the caller's input rather than in the persisted chart.

**Why `--keep-dependents` is exempt.** Reordering it would change a documented output array for a code path that has no defect. The cost is a small asymmetry in the closure's contract; the benefit is not breaking callers to fix a bug they cannot hit.

## Early proof point

Task fn-153-chart-graph-integrity-premise-ordered.1 validates the cascade fix, which is the harder of the two. The fixture is buildable through the public CLI - `chart wire-decision` accepts `--depends-on`, validates atomically, and is already exercised by real-CLI tests - so the recipe is concrete: create D1 through D3, `wire-decision D2 --depends-on D3`, `wire-decision D3 --depends-on D1`, resolve D2 and D3, then `resolve D4 --supersedes D1`. The file's `_add_decision` helper allocates strictly in creation order and cannot produce this shape on its own; `wire-decision` is what makes it reachable.

If premise-first ordering cannot be introduced without breaking the existing supersession pins (`TestSupersession`), stop and report rather than loosening those tests - they encode the cascade contract this spec is trying to strengthen.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Premise-first cascade wiring | .1 | - |
| R2 | Collision defined by owner; same-owner registration idempotent | .2 | - |
| R3 | Regression tests, gate, propagation, no bump | .1, .2 | - |
| R4 | Initial-map: all four write sites, both directions | .2 | - |
| R5 | Sharpen: batch ordinals removed from the namespace | .2 | - |
| R6 | Deterministic Kahn order; exact arrays asserted | .1 | - |
| R7 | `--keep-dependents` ordering preserved via call-site separation | .1 | - |
| R8 | `alias_collision` code + stable asymmetric details schema, documented | .2 | - |
| R9 | Single shared helper, parameterized by namespace policy | .2 | - |
| R10 | Atomic rejection demonstrated (no files, no consumed D-number) | .2 | - |
| R11 | New-versus-new sharpen collision covered | .2 | - |
| R12 | Both public doc contracts pinned in the docs inventory | .2 | - |

## References

- Cascade: `_depends_on_closure` `13040-13059` (sort at `13058`); `_depends_on_reverse_index` `13027-13037`; sole caller `13602`; `premise_rewrite` seeded `13634`, read `13686`, written `13724`; open-dependent branch `13639-13666`; `--keep-dependents` branch `13606-13624`
- Aliasing: initial-map `11814-11863` (writes `11846`, `11847`, `11848`, `11851`); sharpen `13814-13872` (writes `13847`-`13850`, `13852`); existing-decision fold `13865-13871`; shared reader `_normalize_edge_refs` `11345-11378`
- Validation: `validate_chart_graph` `11381-11489` (cycle check `11462-11486`), called `11896` and `13925`; `ChartError` `10082-10100`; `CHART_ERROR_CLASSES` `195-205`; envelope `chart_fail` `10151-10166`
- Double-call site: `validate_and_build_initial_map` invoked at `23329` and `23345`
- Tests: `test_chart_resolution.py` `TestSupersession` `582-828` (`test_replacement_rebinds_premises_to_superseding_decision` `691-771` documents the bug class but only exercises sequential single-dependent cascades); `test_chart_graph_claims.py` `TestGraphValidation` `311-435`, `TestInitialMapMaxDecisions` `1121-1287` (no test supplies a caller `id` today); real-CLI helper `_run_flowctl` (`test_chart_resolution.py:60-76`)
- fn-154 overlap: **none**. Verified by `git diff main fn-154-...` - that branch touches `_briefing_fingerprint`, `emit_chart_briefing`, `cmd_chart_briefing` only. Re-run `test_chart_briefing.py` after both land, whichever merges second: its `_resolve` helper calls `chart resolve --supersedes` as black-box setup.

# fn-153 chart graph integrity: premise-ordered cascades and unambiguous map aliases

## Goal & Context
<!-- scope: business -->

Two chart-graph defects were found by the cross-family review of fn-135 and deliberately deferred at merge, on the reasoning that neither is reachable from the shipped `/flow-next:chart` skill's own code path. That reasoning holds only for the skill. `flowctl chart` is a public CLI surface that autonomous drivers, scripts, and other harnesses call directly, and the store's guarantees are the product: a chart that silently persists the wrong graph is worse than one that refuses, because supersession and briefing both read that graph as truth later.

Both defects are silent. Neither raises, neither logs; each produces a chart that looks correct and answers a later question wrongly. That is the specific failure class the chart store exists to prevent, so they get closed rather than documented.

This is deliberately the smallest possible spec: two narrow correctness fixes in one module, no new surface, no behavior anyone is currently relying on.

## Architecture & Data Models
<!-- scope: technical -->

**1. Cascade ordering (`_depends_on_closure`, `flowctl.py:13040`).** The closure walk collects transitive dependents, then sorts them by local D-number before returning. `resolve_chart_decision` consumes that order and builds its `premise_rewrite` map incrementally as it creates each replacement. When D-numbering is non-topological - D2 depends on D3, D3 depends on D1 - the sort returns D2 before D3, so D2's replacement is constructed before the map knows D3's replacement id. The new decision is then wired to the superseded D3 rather than to its replacement, and a later reversal of that replacement cannot reach it through the closure.

The fix is ordering, not a new mechanism: return the closure in premise-first (topological) order over the `depends_on` edges being walked, falling back to local-number order only to break genuine ties, so a dependent is never processed before a dependent it itself depends on. The graph is already cycle-validated at write time, so a topological order always exists.

**2. Initial-map and sharpen alias collisions (`validate_and_build_initial_map`, `flowctl.py:11846`; the sharpen path at `13847`).** Both passes populate `local_map` with generated aliases (`1`, `d1`, the full D-ID) and then, if the input supplies an optional `id`, that value too - by plain assignment. Two decisions sharing an explicit `id`, or an explicit `id` colliding with another decision's generated alias (a decision literally keyed `"d1"`), overwrite the earlier entry. Every `blocked_by` / `depends_on` reference using that alias then resolves to the last writer, and the chart persists a valid-looking graph wired to the wrong decisions.

The fix is validation before use: reject a proposal whose alias namespace is ambiguous, naming the colliding alias and both decision indices, before any D-ID is allocated or any file is written. Both entry points share the aliasing logic and must share the check.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Supersession cascades process dependents in premise-first order, so a replacement created for a dependent is wired to the replacement of any premise that this same cascade superseded, never to the superseded premise itself. Proven with a non-topological chart (D2 depends on D3, D3 depends on D1, both resolved; D4 supersedes D1): both replacements exist, the replacement of D2 depends on the replacement of D3, and a subsequent supersession reaches the whole chain.
- **R2:** Alias uniqueness is validated across the generated (`<n>`, `d<n>`, full D-ID) and caller-supplied (`id`) namespaces in both the initial-map and resolve-sharpen paths. A duplicate or colliding alias is rejected atomically with a `validation` error naming the alias and the conflicting entries, before any D-ID allocation or file write; the pre-existing no-collision behavior is unchanged.
- **R3:** Both fixes carry regression tests in the existing chart suites, and the full repository gate plus the fn-135 propagation chain (dual `.flow/bin` copies, tracker manifest, `sync-codex.sh` twice, byte-idempotent) stay green. No version bump.

## Boundaries
<!-- scope: business -->

- **No new commands, flags, config keys, or envelope fields.** Both fixes are internal to existing operations.
- **No re-litigating the deferral.** The two findings are accepted as real; this spec closes them rather than re-deciding them.
- **Not a general graph-semantics review.** Only the two named defects. Anything else the work surfaces is captured, not fixed here.
- **No skill or docs changes.** The `/flow-next:chart` prose is unaffected because the skill never emits explicit ids and allocates breadth-first; only the deterministic store changes.

## Decision Context
<!-- scope: both -->

**Why fix at all, given neither is reachable from the skill.** The store is the contract, not the skill. fn-135 shipped `flowctl chart` as a documented CLI with `--json` envelopes precisely so autonomous drivers and other harnesses could drive it, and the spec's own R14/R38 make the graph guarantees explicit. A guarantee that holds only when our own prose is the caller is not a guarantee.

**Why order rather than a second pass.** The cascade could instead pre-allocate every replacement id before wiring any of them, which also fixes R1. Premise-first ordering is smaller, keeps allocation and wiring adjacent, and makes the invariant legible at the point it matters: you cannot rewrite a premise you have not replaced yet. The topological order is guaranteed to exist because the graph is already cycle-validated before any write.

**Why reject rather than disambiguate aliases.** A colliding alias has no correct interpretation - the caller meant one of two decisions and we cannot know which. Silently taking the last writer is the current bug; taking the first would be an equally arbitrary guess. Refusing before allocation matches how every other invalid graph input is handled (missing targets, self-edges, duplicate edges, cycles) and keeps the failure at the caller's input rather than in the persisted chart.

## Quick commands
<!-- scope: technical -->

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

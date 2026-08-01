---
satisfies: [R1, R3, R6, R7]
---
# fn-153-chart-graph-integrity-premise-ordered.1 Premise-first cascade ordering (Kahn, number tie-break); keep-dependents exempt

## Description
Make supersession cascades wire replacements to replacements, not to the premises this same cascade just superseded.

`_depends_on_closure` (`flowctl.py:13040-13059`) walks a reverse index by DFS and then **sorts by local D-number at line 13058**. `resolve_chart_decision` consumes that order and builds `premise_rewrite` incrementally - a resolved dependent's replacement id is registered at `13724`, after its own rewiring already read `premise_rewrite.get(p, p)` at `13686`. With non-topological numbering (D2 depends on D3, D3 depends on D1) D2 is processed first and its replacement is wired to the **superseded** D3.

Return the closure premise-first instead. **The algorithm is specified: Kahn's algorithm with a min-heap keyed on local D-number.** Not DFS post-order - both are topologically valid, but only the heap variant makes "local-number order to break genuine ties" true as written, and only a fully determined order keeps the public `--json` arrays (`affected`, `cascade_open`, `cascade_resolved`, `replacements`) reproducible for autonomous drivers. A topological order always exists: `validate_chart_graph` cycle-checks the same `depends_on` edge set before every persisted write.

**`--keep-dependents` is exempt.** Its branch (`13606-13624`) has no cross-iteration data dependency and no correctness defect. Reordering it would churn a documented output array for callers who cannot hit either bug. Keep it emitting in local-number order and pin that with a test.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_resolution.py`, plus the propagation targets

### Approach

- Follow the existing helper style in the same region; `_depends_on_reverse_index` (`13027-13037`) already gives you the adjacency you need.
- Tests go in `test_chart_resolution.py` and drive the REAL CLI through its existing `_run_flowctl` subprocess helper (`:60-76`).
- **Fixture warning:** the file's `_add_decision` helper (`:94`) allocates D-numbers strictly in creation order, so it CANNOT produce the non-topological graph R1 needs. Build it with `chart wire-decision` or a batch `chart create --initial-map-file` payload.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:13027-13059` - the reverse index and the closure
- `plugins/flow-next/scripts/flowctl.py:13602-13785` - the cascade: `premise_rewrite` seeded `13634`, read `13686`, written `13724`; open-dependent branch `13639-13666`; `--keep-dependents` branch `13606-13624`
- `plugins/flow-next/scripts/flowctl.py:13979-14009` - the transaction call and the reported cascade arrays
- `plugins/flow-next/tests/test_chart_resolution.py:582-828` - `TestSupersession`, especially `test_replacement_rebinds_premises_to_superseding_decision` (`691-771`), which documents this bug class but only exercises sequential single-dependent cascades and must stay green

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:11415-11489` - the cycle check that guarantees a topological order exists

### Key context

Do NOT try to fix an *open* dependent's stale `depends_on`. Only resolved dependents flow through `premise_rewrite`; an open one gets a `premise_invalidated` note and keeps its edge pointing at the superseded id. That is a separate structural decision and the spec puts it explicitly out of scope - premise-first ordering cannot address it.

If the non-topological fixture turns out to be unbuildable through the public CLI, the defect is unreachable by any caller: STOP and report rather than shipping an unprovable fix.

`flowctl.py` edits require the propagation chain or `test_tracker_distribution` fails: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` (never overwrite the bash launcher `.flow/bin/flowctl`), `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`, `python3 scripts/gen_tracker_manifest.py`, then `./scripts/sync-codex.sh` twice.

### Acceptance
- [ ] `_depends_on_closure` returns premise-first order via Kahn + min-heap on local D-number; the tie-break is ascending D-number (R1, R6)
- [ ] Real-CLI test on a non-topological chart (D2 depends on D3, D3 depends on D1, both resolved; D4 supersedes D1): both replacements exist, the replacement of D2 depends on the **replacement** of D3, and a subsequent supersession reaches the whole chain (R1)
- [ ] Test asserts the exact emitted order on a graph with a genuine tie, proving determinism (R6)
- [ ] Test pins that `--keep-dependents` still emits dependents in local-number order (R7)
- [ ] `TestSupersession`'s existing tests pass unmodified (R3)
- [ ] Propagation chain run; `cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution test_chart_graph_claims test_chart_store -q` green

## Acceptance
- [ ] Premise-first closure via Kahn + min-heap on local D-number
- [ ] Non-topological cascade test: replacement wired to replacement, chain reachable by a later supersession
- [ ] Determinism test on a genuine tie
- [ ] `--keep-dependents` ordering pinned unchanged
- [ ] Existing TestSupersession tests unmodified and green
- [ ] Propagation chain run; focused suites green


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

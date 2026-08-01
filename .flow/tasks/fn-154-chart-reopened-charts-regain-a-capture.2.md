---
satisfies: [R1, R3, R7, R8]
---
# fn-154-chart-reopened-charts-regain-a-capture.2 Self-describing emission: discriminator, human output, transition tests

## Description
Make the emission self-describing, and prove the fix holds across the state transitions the first task's mechanism covers implicitly.

Two changes in `plugins/flow-next/scripts/flowctl.py`:

1. **Discriminator on the emission result.** A briefing that supersedes stale predecessors says so, in the `--json` result payload (`emit_chart_briefing`, around `15059-15086`). **The field must NOT be named `outcome`** - that term is already bound to the chart's stated goal (`chart create --outcome`, the `## Outcome` heading, `re-state Outcome` throughout the skill). Pick a name in the emission vocabulary and use it identically in code, docs and tests. Keep per-briefing `status` in `chart show --json` as the single source of truth for capture-readiness - the discriminator explains what this invocation did, it does not replace the status field a consumer gates on.
2. **The human print branch.** `cmd_chart_briefing`'s non-JSON branch (`24248-24259`) can currently only print `status=<val> (noop)` plus an optional `transitioned_done` line - which is exactly the misleading output the bug report describes. Add the case so a terminal user sees what happened.

Then the transition tests. These pass by construction if task .1's mechanism is right, which is the point: they pin that it stays right.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_briefing.py`, plus the propagation targets

### Approach

- Envelope shape is `chart_json_success(command, result)` (`flowctl.py:10103-10116`); the result dict for a fresh emission is built at the end of `emit_chart_briefing`. Follow the existing key style (`noop`, `chart_status`, `clusters`, `paths`).
- The non-JSON branch mirrors how `cmd_chart_reopen` (`24262-24301`) prints its human summary.
- Tests use the real-CLI `_run_flowctl` helper as in task .1.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:15059-15086` - the fresh-emission result payload
- `plugins/flow-next/scripts/flowctl.py:24203-24260` - `cmd_chart_briefing`, especially the non-JSON print branch at 24248-24259
- `plugins/flow-next/scripts/flowctl.py:14874-14890` - where `briefing_status` (draft vs final) is computed per invocation
- `plugins/flow-next/scripts/flowctl.py:15100-15120` - `reopen_chart`'s legal source states (`done` and `abandoned`)
- `plugins/flow-next/tests/test_chart_briefing.py:302-334` (`TestForcedDraft`), `1438-1466` (`TestReopenFromAbandoned`)

### Key context

`reopen` flattens BOTH `draft` and `final` briefings to `stale` (`flowctl.py:15130-15139`), so a stored per-briefing status cannot tell them apart afterwards. Draft-vs-final must therefore be decided from the freshly recomputed briefable state plus THIS invocation's `--force`, never from a predecessor's record. That is the R7 test's whole point.

`chart abandon` is legal only from `open` and never touches briefings, so a chart can reach `abandoned` still carrying a never-finalized briefing - the R8 abandoned-path test covers a real state, not a synthetic one.

`flowctl.py` edits require the propagation chain (see task .1 Key context).

### Acceptance
- [ ] The fresh-emission `--json` result carries an explicit discriminator naming that this emission superseded stale predecessors
- [ ] The discriminator is NOT named `outcome`, and the chosen name is used identically in code, tests and docs (R9 wording lands in task .3)
- [ ] `chart show --json` per-briefing `status` is unchanged and remains the capture-readiness source of truth (R3)
- [ ] The non-JSON print branch reports the superseding emission instead of only `status=... (noop)`
- [ ] Real-CLI test: a chart whose only briefing is a staled `--force` draft does not yield a `final` briefing unless the chart is genuinely briefable, and a `--force` retry after reopen still yields a draft (R7)
- [ ] Real-CLI test: reopen sourced from `abandoned` behaves identically to reopen sourced from `done` (R8)
- [ ] Real-CLI test: a second reopen-then-rebrief round trip mints again rather than re-matching (R8)
- [ ] Propagation chain run; `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff test_chart_tracker_projection -q` green

## Acceptance
- [ ] Fresh-emission result carries an explicit superseded-stale discriminator, not named `outcome`
- [ ] `chart show --json` per-briefing status unchanged and authoritative
- [ ] Non-JSON branch prints the superseding emission case
- [ ] R7 draft-recompute test passes
- [ ] R8 abandoned-source test passes
- [ ] R8 second-round-trip test passes
- [ ] Propagation chain run and the three focused suites green


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

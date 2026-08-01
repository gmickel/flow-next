---
satisfies: [R1, R3, R4, R7, R8, R9]
---
# fn-154-chart-reopened-charts-regain-a-capture.2 Self-describing emission: discriminator, human output, transition tests

## Description
Make the emission self-describing, and prove the fix holds across the state transitions the first task's mechanism covers implicitly.

Two changes in `plugins/flow-next/scripts/flowctl.py`:

1. **`supersedes_stale` on the emission result.** The contract is fixed by the spec, not chosen here:
   - **Field:** `supersedes_stale`
   - **Type:** array of B-ID strings (`["B1"]`), in sidecar order
   - **Presence:** ONLY on a fresh emission (`noop: false`) that follows at least one `stale` briefing, and only when non-empty. Absent from every idempotent-retry result, every first-emission result, and every error envelope.
   Presence is the discriminator. Absence is what keeps existing envelopes byte-identical - do not add the key with an empty array on other paths, that would break R4. Keep per-briefing `status` in `chart show --json` as the single source of truth for capture-readiness; `supersedes_stale` says what this invocation did, it does not replace the field a consumer gates on. It is not named `outcome` because that term is already bound to the chart's stated goal.
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

`chart abandon` is legal only from `open` and never touches briefings, so a chart can reach `abandoned` still carrying a never-finalized briefing. That is exactly why the R8 abandoned sequence must start by force-drafting B1: abandon a chart with NO briefing and the later reopen-then-brief just mints B1, exercising nothing.

`flowctl.py` edits require the propagation chain (see task .1 Key context).

### Acceptance
- [ ] `supersedes_stale` ships with exactly the name, array-of-B-ID type, and presence rule the spec fixes (R9)
- [ ] A test asserts `supersedes_stale` is ABSENT from a first-emission envelope and from an idempotent-retry envelope - this is what makes R4's byte-unchanged claim checkable
- [ ] `chart show --json` per-briefing `status` is unchanged and remains the capture-readiness source of truth (R3)
- [ ] The non-JSON print branch reports the superseding emission instead of only `status=... (noop)`
- [ ] Real-CLI test: a chart whose only briefing is a staled `--force` draft does not yield a `final` briefing unless the chart is genuinely briefable, and a `--force` retry after reopen still yields a draft (R7)
- [ ] Real-CLI test (R8, exact sequence - a loose 'behaves identically' assertion is vacuous): open chart with an UNRESOLVED decision -> `briefing --force` mints draft B1, chart stays open -> `abandon` -> `reopen` -> `briefing --force` with the IDENTICAL proposal -> B1 is stale and a new DRAFT B2 is minted, and it does NOT become final (the chart is still unbriefable)
- [ ] Real-CLI test (R8, exact sequence): continue the done-sourced R1 path - after final B2 and chart `done`, `reopen` again -> `briefing` with the identical proposal -> final B3 and chart `done`, proving a second reopen mints rather than re-matching B2
- [ ] Propagation chain run; `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff test_chart_tracker_projection -q` green
## Acceptance
- [ ] `supersedes_stale` ships with the spec's exact name, type and presence rule; absent on first-emission and idempotent-retry envelopes
- [ ] `chart show --json` per-briefing status unchanged and authoritative
- [ ] Non-JSON branch prints the superseding emission case
- [ ] R7 draft-recompute test passes
- [ ] R8 abandoned-source test passes via the exact force-draft sequence (draft B2, never final)
- [ ] R8 second-round-trip test passes (final B3 after a second reopen)
- [ ] Propagation chain run and the three focused suites green
## Done summary
Made the briefing emission self-describing: a fresh emission that supersedes stale predecessors now carries `supersedes_stale` (array of B-IDs in sidecar order, present only on that path, so retry/first-emission/error envelopes stay byte-identical), and the non-JSON branch names the minted B-ID plus the superseded ones instead of the misleading `status=stale (noop)` line from the bug report. Added real-CLI transition tests pinning per-invocation draft/final recompute (R7), the abandoned-source and second-round-trip reopen sequences (R8), and the discriminator's presence/absence rules (R9/R4); the six behavioural ones were verified to fail against the pre-fix binary.
## Evidence
- Commits: 8c7a10a4eaeda4c6e0b4f73514912e26dbe1ee04, ff0076aaf47f8a3ceb0e21ee99e2782020dec412, 35e74c235540cda55006c7fc92b2ca36e701d3b6
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff test_chart_tracker_projection -q (90 tests, OK), cd plugins/flow-next/tests && python3 -m unittest test_tracker_distribution test_startup_bootstrap test_chart_docs_inventory test_prompt_text_pinned -q (64 tests, OK), uvx ruff@0.16.0 check . (All checks passed), bite check: the 6 new transition/discriminator tests fail against the pre-fix binary (worktree at 00504e00); only the byte-unchanged regression passes on both sides, baseline: green (focused suites green pre-edit)
- PRs:
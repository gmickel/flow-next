---
satisfies: [R1, R2, R7]
---

## Description

The flowctl plumbing: a lazy on-disk `ready` boolean, `spec ready`/`spec unready` subcommands, explicit-false JSON exposure on all three read surfaces, a ready-only badge in human listings, and the test/CI wiring.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_spec_ready.py` (new), `.github/workflows/test-flow-next.yml`, `plugins/flow-next/scripts/ci_test.sh`, `plugins/flow-next/scripts/smoke_test.sh`, `plugins/flow-next/scripts/alias_smoke.sh`, `.flow/bin/flowctl.py` (re-copy)

## Approach

Per the spec's "Resolved at planning" section (read it first — it IS the contract):
- **Lazy on-disk**: `spec create` (:11591) does NOT write the key; `normalize_epic` (:2152) does NOT backfill it (would defeat lazy purity on next write). Read surfaces default explicitly.
- **Commands**: clone `cmd_spec_set_plan_review_status` (:12380 — it normalizes on load; do NOT clone `cmd_spec_close`, it doesn't). `ready` writes true / `unready` writes false — both **idempotent no-ops** (no write, no `updated_at` bump) when the value is already there or the key is absent+false. Reject `.M` task ids with a clear error; allow `done` specs (status-orthogonal). `cmd_epic_ready`/`cmd_epic_unready` alias lines (pattern at :17211). Spec id routes through `resolve_spec_id_arg` (tracker handles resolve — id-grammar memory).
- **Subparsers**: in the spec/epic noun loop near `set-branch` (:23961); shape = positional `id` + `--json` (clone `close` parser :23984).
- **JSON surfaces** (gap-analysis blocker #2): `cmd_specs` (:12091) and `cmd_list` (:12259) build explicit dicts — add `"ready": spec_data.get("ready", False)` to BOTH; `cmd_show`'s spread (:12014) omits an absent key — add the explicit default to its result too. All three must emit `ready: false` for a not-ready spec, never omit.
- **Badge**: human output in `cmd_specs` (:12123) and `cmd_list` (:12297) — marker ONLY on ready specs (no draft-noise for non-adopters, clig.dev color-restraint).
- **Tests** (`test_spec_ready.py`, model `test_tracker_receipts.py` harness): lazy purity (create → no key on disk, JSON reports false), toggle round-trip, idempotent no-ops ("unready on never-ready spec leaves sidecar byte-identical"), unknown-key round-trip preservation, `.M` rejection, tracker-handle resolution, `done`-spec allowed. CI: explicit `-p "test_spec_ready.py"` step (no catch-all). `ci_test.sh` + `smoke_test.sh` gain spec ready/unready + badge cases (ride existing CI steps); `alias_smoke.sh` gains epic-alias parity. Re-copy dogfood `.flow/bin/flowctl.py`.

## Investigation targets

**Required:**
- `.flow/specs/fn-58-spec-readiness-signal-ready-flag.md` §Resolved at planning
- `plugins/flow-next/scripts/flowctl.py:12380-12417` — clone source + alias pattern
- `plugins/flow-next/scripts/flowctl.py:12091-12124, 12259-12298, 12014` — the three output surfaces
- `plugins/flow-next/scripts/flowctl.py:2152-2155, 11591` — normalize_epic + create (do-NOT-touch contract)

**Optional:**
- `plugins/flow-next/tests/test_tracker_receipts.py` — in-process `_call` harness
- `.github/workflows/test-flow-next.yml:75-278` — explicit -p step pattern

## Acceptance

- [ ] Fresh `spec create` writes no `ready` key; `show/specs/list --json` all emit explicit `"ready": false` for it
- [ ] `spec ready`/`unready` toggle + are idempotent no-ops (byte-identical sidecar, no `updated_at` churn); `.M` ids rejected; `done` specs allowed; epic aliases + tracker handles work
- [ ] Badge appears in `specs`/`list` human output ONLY for ready specs
- [ ] Unknown-key round-trip regression test passes; full suite green; new test file wired into CI; smoke/alias scripts extended
- [ ] Dogfood copy byte-identical

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: spec ready/unready verbs, lazy flag, JSON ready booleans and [ready] badges all live (used in this very session to mark fn-160/163/164/165). No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs:
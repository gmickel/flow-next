---
satisfies: [R1, R2, R3, R7, R8]
---

## Description

Add the flowctl plumbing for observable lifecycle touchpoints: an `--event` tag on `sync receipt`, and a new read-only `sync check` command — the first-ever reader of `.flow/sync-runs/`. Plus tests and CI wiring.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_sync_check.py` (new), `plugins/flow-next/tests/test_tracker_receipts.py` (extend), `.github/workflows/test-flow-next.yml`, `.flow/bin/flowctl` (re-copy for dogfood parity)

## Approach

- `--event`: add to the `receipt` subparser (`flowctl.py:23190-23208`, mirror `--transport` at :23201) as a **free-form string with `default=None`** — NOT `choices=` (perEvent keys are an open extension point, R7; see also memory `fn-44-review-cycle-lessons` on choices= rejecting before the handler). Add the key to the receipt dict at `cmd_sync_receipt` :20331-20340 via `getattr(args, "event", None)` (the file's backward-compat idiom). Existing callers are unaffected.
- `sync check <spec-id> --events <csv> --since <iso> [--json]`: new subparser after `defer` (:23210). Handler clones the read-only enumerator shape of `cmd_sync_list_stale` (:20178) / `cmd_sync_check_collisions` (:20220) — `ensure_flow_exists()` → early exit → iterate → JSON-vs-plain output branch.
  - **First gate:** `tracker_sync_active()` (:1334) false → return silently, exit 0, zero output (R8). Before ANY receipt I/O.
  - Spec id routes through `resolve_spec_id_arg` (:4520) — the id-grammar memory (`id-grammar-widening-must-cover-the-full`): fn-52 missed `sync receipt`/`defer`; do not repeat for `check`.
  - `--events`: comma-split single string (not `nargs="+"`). `--since`: ISO timestamp; parse via the existing `_parse_iso_ts` helper — bare `fromisoformat` crashes on `Z` suffixes under Python 3.8-3.10.
  - Glob `.flow/sync-runs/sync-*.json` (`SYNC_RUNS_DIR_REL` :19690), filter on receipt `id` == spec, `event` ∈ events, `timestamp ≥ --since`. Receipts with `event: null` (pre-flag) never satisfy an event check.
  - Per the spec's "Check semantics": MISSING iff triggered ∩ perEvent-enabled (read leaves via `get_config`, schema at :1052-1080 — note `work.*` keys are nested) ∩ bridge-active ∩ no-matching-receipt. Linkage is NOT a precondition. ANY receipt status clears. Configured-but-not-passed events are not evaluated.
  - Output: one `OK:<event>` / `MISSING:<event>` line per event (plain), or `{"events": [...], "missing": [...], "count": N}` (--json). Exit 0 always (best-effort contract; output drives agent action, not exit code).
- **No tracker-mutation code** anywhere in this task (R3 negative constraint).
- Tests: new `tests/test_sync_check.py` mirroring `test_tracker_receipts.py` setUp (importlib + in-process `_call`, tempdir + git init). Extend `test_tracker_receipts.py` with `test_receipt_records_event`. **CI:** `.github/workflows/test-flow-next.yml` has NO catch-all — add explicit `-p "test_sync_check.py"` AND `-p "test_tracker_receipts.py"` steps (the latter is not in CI today).
- Re-copy `plugins/flow-next/scripts/flowctl.py` → `.flow/bin/flowctl` (dogfood parity; the copy is currently stale from May 27 — flag if diff is large).

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:20293-20359` — `cmd_sync_receipt` (receipt dict, atomic write, id canonicalization at :20309)
- `plugins/flow-next/scripts/flowctl.py:23104-23219` — sync subparser group (where `check` slots in)
- `plugins/flow-next/scripts/flowctl.py:20178-20246` — `cmd_sync_list_stale` + `cmd_sync_check_collisions` (the read-only enumerator idiom to clone)
- `plugins/flow-next/scripts/flowctl.py:1334-1357` — `tracker_sync_active()` (zero-overhead gate); :1052-1080 perEvent schema
- `plugins/flow-next/tests/test_tracker_receipts.py` — test harness pattern (`_call`, `_receipt` helpers)

**Optional:**
- `plugins/flow-next/tests/test_qa_tracker_event.py` — subprocess CLI harness style (if argparse wiring needs e2e coverage)
- `.github/workflows/test-flow-next.yml:79-252` — the 18 explicit `-p` steps pattern

## Acceptance

- [ ] `sync receipt --event work.firstClaim` writes the `event` field; omitting `--event` produces today's receipt shape + `event: null` — no existing caller breaks
- [ ] `sync check` on a bridge-inactive repo prints nothing, exits 0, in constant time (R8)
- [ ] `sync check` reports `MISSING:<event>` only per the spec's full predicate; any-status receipt ≥ `--since` clears it; `event: null` receipts never clear an event check
- [ ] `--since` with `Z`-suffixed ISO parses on Python 3.8 (regression test); tracker handles (e.g. `FLOW-10`) resolve as the spec id
- [ ] No tracker-mutation code added to flowctl (R3)
- [ ] `test_sync_check.py` + `test_tracker_receipts.py` run in CI via explicit workflow steps; full suite green locally
- [ ] `.flow/bin/flowctl` re-copied and byte-identical to canonical

## Done summary
Added `--event <perEvent-key>` to `flowctl sync receipt` (free-form, `event: null` back-compat) and the new read-only `flowctl sync check <spec-id> --events <csv> --since <iso> [--json]` — the first reader of `.flow/sync-runs/`, with the R8 silent constant-time gate before any IO, the full MISSING predicate (triggered ∩ perEvent-enabled ∩ bridge-active ∩ no event-matching receipt ≥ --since), any-status-clears, and exit-0-always. Shipped with 19 new tests + 3 receipt-tag tests, explicit CI steps for both suites, and a byte-identical dogfood re-copy; no tracker-mutation code added (R3).
## Evidence
- Commits: d9670921512047c9d76e8502c6d795cfb78a0ac7
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_sync_check.py -v (19 OK), python3 -m unittest discover -s plugins/flow-next/tests -p test_tracker_receipts.py -v (13 OK), python3 -m unittest discover -s plugins/flow-next/tests (1033 OK, 2 skipped), python3 -m py_compile plugins/flow-next/scripts/flowctl.py, scratch-repo smoke: inactive silent exit 0 -> MISSING:capture -> receipt --event -> check --json count 0, live-repo smoke: sync check FLOW-10 resolves canonical id, pre-flag receipts read MISSING, exit 0, read-only
- PRs:
---
satisfies: [R21, R22]
---
# fn-134-spec-id-collisions-widen-allocation.7 flowctl papercuts: task set-title, converged-review exit code

## Description

Two flowctl papercuts found while planning fn-134 itself. Neither relates to spec-id collisions; both are small, atomic, zero-judgment gaps folded in here rather than spawning a spec each.

**Size:** S
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (+ byte-identical `.flow/bin/flowctl.py`)

**Sequencing:** this task depends on `.3` as well as `.2`. Both `.3` and `.7` may touch `flowctl.py`, its `.flow/bin` copy, and the bootstrap hashes; even non-overlapping source edits collide on the copied files and `SOURCE_SHA256`, so they must not run concurrently.
- `plugins/flow-next/scripts/flowctl_bootstrap.py` (+ `.flow/bin/` copy), `flowctl-help.txt` + `HELP_SHA256` (the argparse surface DOES change here)
- `plugins/flow-next/tests/test_flowctl_surface.py` (CLI surface snapshot), plus a test for each fix
- `plugins/flow-next/docs/flowctl.md`

## Approach

**Fix 1: `task set-title`.** `flowctl task` has `create`, `set-description`, `set-acceptance`, `set-spec`, `reset`, `set-backend` and no way to rename after creation. Add `task set-title <task-id> --title "..."`.

The subtle part is the **dual representation**: a task's title lives in BOTH `.flow/tasks/<id>.json` (`title`) and the markdown H1. `task set-spec --file` today rewrites the H1 and leaves the JSON untouched, so the two silently disagree - the markdown says one thing and `flowctl tasks` lists another. Fix both directions: `set-title` writes both, and `set-spec --file` either keeps them in sync or refuses to change the H1. Do not add a third place a title can live.

**Fix 2: a converged review exits non-zero.** On SHIP, the reset-on-convergence helper pops the pending reservation (`flowctl.py:7070-7073`); the finalize path then sees `pending_count == 0` and calls `error_exit(..., code=2)` (`:6888-6898`). Observed live on this spec's own round 3: verdict written, `plan_review_status` set to `ship`, counter reset - and still a non-zero exit.

Pick ONE of exactly TWO safe resolutions and say why: **finalize consumes the reservation before reset clears it**, or **reset stops clearing pending reservations**.

**Do NOT simply make finalize tolerate a zero-pending verdict.** It reads like the smallest fix and it is the wrong one: finalize cannot tell "cleared by this attempt's own reset" apart from an unreserved, duplicated, or stale verdict, so tolerating zero-pending would let a duplicate verdict finalize and would hole the reservation invariant the deterministic round cap rests on. Allowing it at all would require introducing **attempt identity** so finalize can prove it is the same attempt that reserved - a bigger change than either safe option.

The **no-verdict transport-failure refund path must keep working exactly as it does now** - that path is what the round cap depends on, and breaking it would be a much worse regression than the bug being fixed.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:6860-6930` - the finalize/refund helper and the `pending_count < 1` hard exit
- `plugins/flow-next/scripts/flowctl.py:7043-7080` - the reset-on-convergence path that pops the reservation
- `plugins/flow-next/scripts/flowctl.py:15583-15596` - the other pending-clearing site (`review-rounds reset`)
- the `task` subparser registration, for where `set-title` belongs

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_flowctl_surface.py:98-106` - the literal CLI surface snapshot

## Key context

**The argparse surface changes in this task**, unlike `.1` and `.2`. That means `flowctl-help.txt` must be regenerated and `HELP_SHA256` re-pinned in both bootstrap copies, on top of the usual `SOURCE_SHA256` re-pin and byte-identical `.flow/bin/` copies. The CLI surface snapshot test must gain `task set-title`.

Test the production argparse routing, not a mock-patched helper: the two-token `task set-title` form is exactly the shape a parallel construction would get wrong.


## Acceptance

- [ ] `flowctl task set-title <task-id> --title "..."` exists and updates the JSON `title` and the markdown H1 together (R21).
- [ ] `task set-spec --file` can no longer leave the JSON title and the markdown H1 disagreeing: it either syncs both or refuses to change the H1. A test asserts they match after each path (R21).
- [ ] A verdict-bearing review finalizes cleanly and **exits zero**. A regression test drives a SHIP end to end and asserts exit code 0 plus the correct persisted status and reset counter (R22).
- [ ] The no-verdict transport-failure path still refunds exactly one reserved round, still increments the consecutive-failure count, and still surfaces as before. Covered by its own test so the fix cannot silently break the round cap (R22).
- [ ] The chosen resolution is one of the two safe options (finalize-before-reset, or reset-stops-clearing), stated in the task evidence with its reasoning. Tolerating a zero-pending verdict was NOT chosen, or if it was, attempt identity was introduced to make it sound (R22).
- [ ] **Negative paths still fail**: an unreserved verdict and a duplicate finalize are both rejected, and neither records a second attempt. Covered by tests, so the fix cannot quietly weaken the reservation invariant the round cap depends on (R22).
- [ ] `task set-title` added to the `test_flowctl_surface.py` snapshot; `flowctl-help.txt` regenerated; `HELP_SHA256` and `SOURCE_SHA256` re-pinned in both bootstrap copies; all `.flow/bin/` copies byte-identical.
- [ ] `docs/flowctl.md` documents `task set-title` alongside the other `task` subcommands.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_flowctl_surface test_startup_bootstrap -q` plus the two new tests.

## Done summary

## Evidence

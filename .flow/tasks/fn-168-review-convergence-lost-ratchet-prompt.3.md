---
satisfies: [R3]
---
# fn-168-review-convergence-lost-ratchet-prompt.3 Classifier guard: carried-unverified priors never stall alone (fn-158 regression)

## Description
Stop `flat-trajectory` from firing on a converging loop whose only open items are carried-and-unverified priors — implemented as an inference over the existing digest row, with the fn-158 shape as the named regression and genuine stalls still classifying.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_review_stall_rule` flat-trajectory branch), `plugins/flow-next/tests/` (the suite that covers `_review_stall_rule` — grep for existing coverage before creating a new file), `.flow/bin/flowctl.py` (propagation)

### Approach
- The distinction needs NO new field: `status == "open"` is only ever written at creation (~`flowctl.py:4920`, `:5540`) and carry-forward deep-copies without resetting, so `status == "open" && firstSeenThisRound == false` means "carried, never touched by any ratchet line". An explicitly re-affirmed prior reads `not_fixed`. **Re-verify this holds** on all write paths (initial creation, host structured path, journal backfill ~`:9854`/`:9870`, the `None`/`[]` branches) before relying on it — if some path leaves a carried item at `open` after an explicit resolution, stop and surface it (the no-new-field non-goal would need reopening).
- Guard: within the flat-trajectory branch (~`:11251-11270`), require at least one re-affirmed (`not_fixed`) or fresh (`firstSeenThisRound == true`) open finding in the CURRENT round before declaring a stall. Do not touch `same-not-fixed-lineage` (~`:11231-11249`) or `fresh-introduced-critical` (~`:11272-11283`).
- Named regression fixture: the fn-158 completion shape — round 1 with 6 open, round 2 with the same 6 carried-unverified + 1 new — must NOT classify, and must pass through to a normal round-3 reservation.
- Keep genuine stalls firing: a re-affirmed `not_fixed` overlap across rounds, and an equal-or-growing set of FRESH open findings. Both get explicit tests.
- Digest pairs that fail validation keep today's behavior.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `_review_stall_rule` (~:11187-11284), especially the flat-trajectory branch and how `previous_open`/`current_open` are built
- `plugins/flow-next/scripts/flowctl.py` — `build_review_findings_digest` (~:5954-5984) for the exact row shape (`status`, `firstSeenThisRound`)
- `plugins/flow-next/scripts/flowctl.py` — every `status` write path: ~:4920, :5540 (creation), ~:5178-5206 (carry/overwrite), ~:9854, :9870 (journal recovery)

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_review_findings_receipts.py` and `test_review_convergence_cap.py` — locate existing `_review_stall_rule` coverage before adding a file
- `plugins/flow-next/scripts/flowctl.py` ~:11287-11302 — the stall marker formatting (unchanged)

### Key context
- EARLY PROOF POINT: this task proves the escalations actually stop. If the carried-unverified inference does not cleanly separate "never mentioned" from "re-affirmed open", surface it before .1/.2 land — the non-goal (no new digest field) would have to be reopened.
- Independent of .1/.2 in code: it reads the digest, not the prompt or the parser.
- Tests must drive the production `_review_stall_rule` with real digest rows, not a parallel construction.

## Acceptance
- [ ] Status-lifecycle re-verification recorded in the task summary (every `open` write path checked; inference holds, or the conflict is surfaced instead of coded around)
- [ ] flat-trajectory requires ≥1 re-affirmed (`not_fixed`) or fresh open finding in the current round; no new digest/receipt field added
- [ ] fn-158 regression fixture (6 open → 6 carried-unverified + 1 new) does NOT classify and reaches a normal round-3 reservation
- [ ] Genuine stalls still classify: re-affirmed `not_fixed` overlap, and equal-or-growing fresh open sets
- [ ] `same-not-fixed-lineage` and `fresh-introduced-critical` behavior unchanged (regression-tested)
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_review_findings_receipts test_review_findings_parser -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

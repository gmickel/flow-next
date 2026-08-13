---
satisfies: [R3]
---
# fn-166-flowctl-module-split-importable.1 Unify verdict→status mapping at the canonical helper

## Description
Route every Python verdict→status literal through the existing `_review_status_from_verdict` helper; delete the duplicate inline dicts; document the non-Python independents at the single site. This is a deletion/rerouting refactor, not a new abstraction — the canonical helper already exists.

**Size:** S
**Files:** `plugins/flow-next/scripts/flowctl.py`; `.flow/bin/flowctl.py` (propagation)

### Approach
- FIRST verify the three dicts are equivalent including unknown-verdict fallback semantics (`.get` default vs KeyError vs explicit else): `flowctl.py:9966-9971` (`_REVIEW_VERDICT_STATUS`), `:10741-10745` (inline in `_record_review_attempt_locked`), `:40053-40057` (inline in `_self_write_review_status`). Any divergence: STOP and surface it — do not silently unify.
- Delete the two inline dicts; route both sites through `_review_status_from_verdict`. Then grep exhaustively for any remaining SHIP/NEEDS_WORK/MAJOR_RETHINK/NEEDS_HUMAN → status literals to confirm none remain.
- At the single site, add a short comment documenting the deliberate independents and why: `ralph-guard.py:128` `VALID_RECEIPT_VERDICTS` (pure validation enum; the hook must not import flowctl internals) and `skills/flow-next-ralph-init/templates/ralph.sh:1278-1285` (inverse status→VERDICT bash mapping inside a generated harness script). Neither is touched.
- Propagate: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` then `python3 scripts/gen_tracker_manifest.py` (manifest hashes flowctl.py).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:9960-9980` — canonical helper + dict
- `plugins/flow-next/scripts/flowctl.py:10735-10750` — duplicate site 2 (inside `_record_review_attempt_locked`)
- `plugins/flow-next/scripts/flowctl.py:40045-40060` — duplicate site 3 (`_self_write_review_status`, docstring states the mapping rule)

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:1278-1285` — bash inverse mapping (do NOT touch)
- `plugins/flow-next/scripts/hooks/ralph-guard.py:128` — independent enum (do NOT touch)

### Key context
- `_REVIEW_REPLAY_PRECEDENCE` at `flowctl.py:10952` is adjacent but NOT a mapping site — leave it (its ordering comment is load-bearing).
- Zero behavior change; this is byte-identical CLI surface territory.
- Memory lesson: test production `cmd_*` paths, not parallel constructions.

## Acceptance
- [ ] Exactly one Python verdict→status mapping site remains; former inline dicts deleted and routed through the helper
- [ ] Pre-unification parity check recorded in the task summary (dicts identical incl. fallback semantics), or divergence surfaced instead of unified
- [ ] Comment at the single site documents ralph-guard enum + ralph.sh inverse mapping as deliberate independents with the why
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_review_receipt_schema test_review_json_tallies test_flowctl_surface -q`
- [ ] Propagation done (cp flowctl.py + gen_tracker_manifest.py)

## Done summary
NOT IMPLEMENTED — closed as superseded, 2026-08-13.

This task's work moved in the fn-166 split: launcher + verdict-map work to `fn-190-flowctl-startup-importable-entry-for`, package extraction + distribution integrity to `fn-191-flowctl-review-terminal-machinery`. No code, docs, or tests were produced here; `done` is a lifecycle marker so the parent spec could be closed (`spec close` requires done tasks and flowctl has no supersede terminal). Read the successors.
## Evidence
- Commits:
- Tests:
- PRs:
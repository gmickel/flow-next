---
satisfies: [R5]
---
# fn-190-flowctl-startup-importable-entry-for.1 One verdict→status site: route the two inline duplicates through the canonical helper

## Description
Delete the two duplicated inline verdict→status dicts and route both call sites through the canonical helper that already exists. Deletion and rerouting only - no new abstraction, no signature change. Ordered FIRST because it edits the same module the launcher task edits, and serializing the two avoids a same-file conflict.

**Size:** S
**Files:** `plugins/flow-next/scripts/flowctl.py`; `.flow/bin/flowctl.py` (propagated copy)
**Touches:** [plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, .flow/bin/flowctl_tracker/MANIFEST.json]

### Approach
- Coordinates below were re-derived 2026-08-13 on main @ 9e111db4 and WILL drift - re-grep `_REVIEW_VERDICT_STATUS` and `"MAJOR_RETHINK": "needs_work"` before editing (expect exactly 3 hits for the latter).
- FIRST, verify equivalence including unknown-verdict fallback semantics across all three sites: canonical `_REVIEW_VERDICT_STATUS` + `_review_status_from_verdict` (~:10485-10495), the inline dict inside `_record_review_attempt_locked` (def at ~:10858, dict at ~:11287), and the inline dict inside `_self_write_review_status` (def at ~:41829, dict at ~:41843). As of 2026-08-13 all three are byte-identical with the same `.get()`-returns-None fallback - confirm that still holds and record the check in the task summary. Any divergence: STOP and surface it (R5's error clause), do not unify.
- Delete the two inline dicts, call the helper instead. Then grep exhaustively for remaining SHIP/NEEDS_WORK/MAJOR_RETHINK/NEEDS_HUMAN → status literals to prove none survive.
- At the single site, add a short comment naming the two deliberate independents and why they are NOT consumers: the generated harness template's inverse status→VERDICT bash mapping (`skills/flow-next-ralph-init/templates/ralph.sh`, ~:1278) and its verdict-set validation enum (~:944) - a bash hook must not import CLI internals, and the direction is inverted.
- Leave `_REVIEW_REPLAY_PRECEDENCE` alone: adjacent, not a mapping site, and its ordering comment is load-bearing.
- Propagate per the project instruction file: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`, then `python3 scripts/gen_tracker_manifest.py` (the manifest hashes flowctl.py), then `./scripts/sync-codex.sh` twice.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` around `_REVIEW_VERDICT_STATUS` - canonical helper + docstring
- the two inline-dict bodies inside `_record_review_attempt_locked` and `_self_write_review_status` - the fallback semantics to compare

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh` - the inverse bash mapping (do NOT touch)

### Key context
- Test production `cmd_*` paths, not parallel reconstructions of the mapping.
- Zero behavior change; this is frozen-CLI-surface territory.

### Acceptance
- [ ] Exactly one Python verdict→status mapping site remains; both inline duplicates deleted and routed through the helper (grep for the mapping literal returns 1 hit)
- [ ] Equivalence check recorded in the task summary (all three dicts identical incl. fallback), or divergence surfaced and left unmerged
- [ ] Comment at the single site names the harness inverse mapping and the hook enum as deliberate independents, with the reason
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_convergence_journal test_review_receipt_schema test_flowctl_surface -q`
- [ ] Propagation done (cp flowctl.py, gen_tracker_manifest.py, sync-codex.sh x2) and the tree is clean afterwards

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

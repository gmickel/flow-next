---
satisfies: [R4, R5, R6]
---
# fn-171-setup-block-addressable-block-ids-per.2 setup-block check: read-only verdict verb with exit-code contract

## Description
---
satisfies: [R4, R5, R6]
---

### Description
Add the read-only `check` verb: same classification apply computes, byte-equality first, distinct verdicts, zero writes.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_setup_block_helper.py`, `plugins/flow-next/tests/test_flowctl_surface.py`

### Approach
- `flowctl setup-block check --file F --template T [--id ID] [--json]`.
- Byte-equality FIRST (apply's order): byte-pristine block -> `unchanged`, exit 0 - even when the recorded hash carries the `customized` sentinel.
- Verdict/exit table (spec Architecture item 4): 0 `unchanged`; 2 drift (`template-drift`, `customized`, `hash-absent`); 3 structural (`missing-file`, `missing-markers`, `corrupt`); 1 ordinary errors. Shared states reuse apply's vocabulary; structural verdicts are check-only names.
- Zero writes in EVERY branch: no target write, no meta.json mutation, no hash re-record (apply re-records in the unchanged-with-drifted-hash and refresh branches - check must not). Acquire `_setup_block_lock` briefly for a consistent meta read; never mutate under it.
- JSON: `_setup_block_emit` shape (`target`/`action`/`reason`/`hash`), action = verdict. NO `command` field exists in setup-block emissions and none is added - the verdict vocabulary alone disambiguates check output. Docs must note argparse usage errors also exit 2, so CI recipes distinguishing drift from usage errors key on the JSON verdict.
- CRLF parity with `_setup_block_hash` (2584-2587): CRLF-only diff is not drift. Mixed-line-ending two-span fixture preserves bytes outside the operated span.
<!-- Updated by plan-sync: fn-171.1 shifted setup-block section anchors (new helpers inserted before _setup_block_hash) -->

- Update the `test_flowctl_surface.py:163-164` help pin with the `check` line.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:2856-2912` - apply transition table (`_cmd_setup_block_apply_locked`) to mirror
- `plugins/flow-next/scripts/flowctl.py:2813-2826` - `_setup_block_emit`
- `plugins/flow-next/tests/test_flowctl_surface.py:163-164` - surface pin
<!-- Updated by plan-sync: fn-171.1 used id-parameterized helpers (_setup_block_normalize_id, _setup_block_markers, _setup_block_require_template_pair, _setup_block_is_nested_hashes) inserted at flowctl.py:2555-2660, shifting all downstream setup-block anchors by ~113 lines -->


**Optional:**
- `plugins/flow-next/tests/test_setup_block_helper.py` - fixture helpers from task 1

### Key context
- The read-only guarantee is load-bearing for CI (copy-mode repos gate on it) - fixtures assert meta.json and target bytes unchanged across ALL branches, incl. hash-absent and template-drift.
- Two-blocks-one-file end-to-end (R5): apply A, apply B, hand-edit B -> check A exit 0, check B exit 2 `customized`; stray B marker doesn't affect A.

### Acceptance
- [ ] check verdict + exit-code contract exactly as spec table; byte-equality first incl. the sentinel-but-pristine case (R4)
- [ ] Zero writes in every branch, asserted by fixtures (R4)
- [ ] --json in emit shape (R4)
- [ ] Two-blocks-one-file end-to-end fixture passes (R5)
- [ ] CRLF-only diff not drift; mixed-ending two-span fixture (R6)
- [ ] Surface pin updated
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_setup_block_helper test_flowctl_surface -q`

## Acceptance
- [ ] read-only check verb, byte-first classification, 0/2/3/1 exit contract
- [ ] zero-write fixtures across all branches
- [ ] two-blocks-one-file + CRLF fixtures
- [ ] surface pin updated

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

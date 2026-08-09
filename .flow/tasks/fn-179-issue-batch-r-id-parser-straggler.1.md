---
satisfies: [R1, R2, R3]
---
# fn-179-issue-batch-r-id-parser-straggler.1 flowctl export/validate parser fixes: R-ID suffix regex + criteria shapes + residue count

## Description
Spec fn-179 items 1-2 (#300, #303). Widen _PR_COGNITIVE_AID_RID_RE to ^R[1-9][0-9]*[a-z]?$ (both call sites use the one constant). Rework _export_parse_acceptance_criteria per the spec: title-form and parenthetical-form bold runs recognized, wrapped text captured until next bullet/blank line, residue count of unparsed '- **R' bullets added to the payload. Issue #303's five-bullet repro is the core fixture; keep an R5a positive control.

**Files:** plugins/flow-next/scripts/flowctl.py (`_PR_COGNITIVE_AID_RID_RE`, `_export_parse_acceptance_criteria`) + `.flow/bin/flowctl.py` dual copy; parser/export tests under plugins/flow-next/tests/

## Acceptance
R1, R2, R3 of the spec. #303 repro parses 5/5; residue field present and non-aborting; R4ab and R-4 still rejected.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

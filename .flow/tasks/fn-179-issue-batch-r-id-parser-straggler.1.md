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
Parser fixes per fn-179 R1-R3 (#300, #303). _PR_COGNITIVE_AID_RID_RE widened to ^R[1-9][0-9]*[a-z]?$ (one constant, both validate call sites; R4ab/R-4 stay rejected). Criteria parser rebuilt as _export_scan_acceptance_criteria: line-wise bullet assembly (wrapped text joined until next bullet/blank/sub-bullet), token-anchored recognition stopping at the first **/: boundary (title form **R14 - title**, parenthetical **R15 (note):**), #303 five-bullet repro parses 5/5, R5a positive control kept; _export_parse_acceptance_criteria stays as a thin wrapper preserving the [{id,text,tag}] contract. Residue count surfaced as spec_sections.acceptance_criteria_residue (probe requires a digit so bold prose is not counted; deliberately-rejected spellings stay visible); text mode prints "K unparsed" only when non-zero; never aborts. 25 criteria recovered across 179 repo specs, none lost.
## Evidence
- Commits: ccd9ece
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_acceptance_criteria_parser test_export_traceability test_pr_cognitive_aid test_qa_smoke test_flowctl_surface test_unaddressed_rids_parser test_prompt_text_pinned test_tracker_distribution -q (143 OK), python3 scripts/run_tests_parallel.py (4361 OK)
- PRs:
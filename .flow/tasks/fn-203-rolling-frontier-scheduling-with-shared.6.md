---
satisfies: [R8, R9]
---
# fn-203-rolling-frontier-scheduling-with-shared.6 Phase B finalization: docs, CHANGELOG, platforms note, full gate

## Description
Documentation and gate pass for the beta release. One finalization task per repo convention.

**Size:** M
**Files:** plugins/flow-next/docs/architecture.md (notes-dir + state-dir section), plugins/flow-next/docs/orchestration.md (experimental-alternative pointer), plugins/flow-next/docs/troubleshooting.md (beta failure modes), plugins/flow-next/docs/platforms.md (host-difference note if locking/notes behavior differs per host), CHANGELOG.md (Unreleased) <!-- Updated by plan-sync: fn-203.3 recorded arm 1 as winning architecture; flowctl.md mutex-verb doc section is moot (arm-2-only, task 5 closed unimplemented) -->
**Touches:** [plugins/flow-next/docs/**, CHANGELOG.md, plugins/flow-next/codex/**]

### Approach
- **Pre-existing gap (flagged by .4's reviewer, P1):** the spec's Decision Context records R2's eval outcome but never states the NUMERIC Phase C field window R10 requires (a minimum count of beta-run specs with receipts) - the beta already shipped in .4 without it. Before touching CHANGELOG/docs, propose and record that number in the spec's `## Decision Context` (Edit `.flow/specs/fn-203-rolling-frontier-scheduling-with-shared.md`), since task .3 did not. <!-- Updated by plan-sync: fn-203.4 reviewer flagged Decision Context lacks the numeric R10 field window -->
- Experimental-tier carve-out per adding-skills.md: NO root README or docs/skills.md rows; CHANGELOG entry IS required and must state beta status, invocation, and the Phase C graduation/sunset trigger - repeating the field window this task itself records in the spec's Decision Context (the spec is the authority; the CHANGELOG never defines it). <!-- Updated by plan-sync: fn-203.4 - field window was not recorded by task .3 as originally planned; .6 records it -->
- architecture.md gains the outside-tree notes-dir + runtime-state-dir description (currently absent).
- flowctl.md mutex section: not needed (arm 1 won; no commit-mutex verb ships) <!-- Updated by plan-sync: fn-203.3 recorded arm 1 as winning architecture -->.
- No flow-next.dev changelog entry for an experimental skill - deferred to graduation.
- Gate: python3 scripts/run_tests_parallel.py + uvx ruff@0.16.0 check . + ./scripts/sync-codex.sh twice; verify R8's two pin surfaces (prompt-pin suite green with no hash updates; work-skill prose-pin suites green untouched).
- G1 justification for every prose growth surface stated in the PR body.
## Acceptance
- [ ] Numeric Phase C field window (minimum count of beta-run specs with receipts) recorded in the spec's `## Decision Context` before any other work in this task lands <!-- Updated by plan-sync: fn-203.4 reviewer-flagged pre-existing gap -->
- [ ] Docs updated per the list above; experimental-tier exclusions respected
- [ ] CHANGELOG Unreleased entry names beta status, invocation, and the graduation field-window trigger (matching the spec-recorded window)
- [ ] Full suite + ruff + double sync-codex green; both R8 pin surfaces verified green with zero canonical work-skill diffs
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

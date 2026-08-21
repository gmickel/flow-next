---
satisfies: [R8, R9]
---
# fn-203-rolling-frontier-scheduling-with-shared.6 Phase B finalization: docs, CHANGELOG, platforms note, full gate

## Description
Documentation and gate pass for the beta release. One finalization task per repo convention.

**Size:** M
**Files:** plugins/flow-next/docs/architecture.md (notes-dir + state-dir section), plugins/flow-next/docs/orchestration.md (experimental-alternative pointer), plugins/flow-next/docs/troubleshooting.md (beta failure modes), plugins/flow-next/docs/flowctl.md (mutex verb, only if arm 2 won), plugins/flow-next/docs/platforms.md (host-difference note if locking/notes behavior differs per host), CHANGELOG.md (Unreleased)
**Touches:** [plugins/flow-next/docs/**, CHANGELOG.md, plugins/flow-next/codex/**]

### Approach
- Experimental-tier carve-out per adding-skills.md: NO root README or docs/skills.md rows; CHANGELOG entry IS required and must state beta status, invocation, and the Phase C graduation/sunset trigger (the pre-declared field window) so R10 has a recorded trigger.
- architecture.md gains the outside-tree notes-dir + runtime-state-dir description (currently absent).
- flowctl.md mutex section follows the existing setup-block verb-doc shape (only if arm 2 won).
- No flow-next.dev changelog entry for an experimental skill - deferred to graduation.
- Gate: python3 scripts/run_tests_parallel.py + uvx ruff@0.16.0 check . + ./scripts/sync-codex.sh twice; verify R8's two pin surfaces (prompt-pin suite green with no hash updates; work-skill prose-pin suites green untouched).
- G1 justification for every prose growth surface stated in the PR body.
## Acceptance
- [ ] Docs updated per the list above; experimental-tier exclusions respected
- [ ] CHANGELOG Unreleased entry names beta status, invocation, and the graduation field-window trigger
- [ ] Full suite + ruff + double sync-codex green; both R8 pin surfaces verified green with zero canonical work-skill diffs
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

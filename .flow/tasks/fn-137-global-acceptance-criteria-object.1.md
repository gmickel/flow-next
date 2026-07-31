---
satisfies: [R1]
---
# fn-137-global-acceptance-criteria-object.1 criteria.md grammar + flowctl criteria plumbing

## Description
The criteria object and its deterministic plumbing.

**Size:** S

**Files:** flowctl.py (criteria subcommand: list --json w/ validation; dual-copy checklist applies), tests.

### Approach
- Grammar: `- **G<N>:** <criterion prose>` (mirrors R-ID form; optional trailing scope hint in prose); parse .flow/criteria.md when present; validate unique ids, non-empty, sequential-not-required.
- `flowctl criteria list --json` -> [{id, text}]; absent file -> [] + ok exit (silent no-op everywhere else).
- Zero-cost-absent proof: stage the assertion now as "completion-review prompt assembly output contains no criteria block marker when .flow/criteria.md is absent" - the marker is the canonical heading `## Global acceptance criteria`, exposed as a shared flowctl constant that .2's injection MUST use (test greps the constant, not a re-typed literal). Vacuously green in this task (no injection exists yet), load-bearing after .2. No placeholder plumbing beyond the test + constant.

## Acceptance
- [ ] Grammar parses + validates; absent = clean empty (R1).
- [ ] Focused tests; Quick commands recorded.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

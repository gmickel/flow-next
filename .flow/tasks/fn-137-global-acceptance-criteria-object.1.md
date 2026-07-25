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
- Zero-cost-absent proof: a test asserting the completion-review prompt assembly path (touched in .2) contributes NOTHING when the file is absent - stage the assertion hook now.

## Acceptance
- [ ] Grammar parses + validates; absent = clean empty (R1).
- [ ] Focused tests; Quick commands recorded.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

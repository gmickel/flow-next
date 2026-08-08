---
satisfies: [R3, R4, R5]
---
# fn-180-declared-vs-evidenced-r-id-coverage.3 validate: batched evidence-commit reachability finding

## Description
Spec fn-180 items 2-3 (#302). Three-state finding per evidence.commits[] entry: reachable (silent), present-but-orphaned (finding), non-commit token (ignored). MUST batch: one cat-file --batch-check over all tokens + one membership pass; constant git spawns regardless of commit count. No auto-rewrite anywhere. make-pr must not render an orphaned SHA link unmarked.

## Acceptance
R3, R4, R5 of the spec. Fixture covers all three states incl. foreign-hex survival; spawn count asserted or inspected.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

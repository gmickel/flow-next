---
satisfies: [R1, R2]
---
# fn-136-structured-review-artifact-schema-in.2 Deterministic finding parser in flowctl

## Description
Pure-stdlib parser: reviewer markdown -> findings[] per the schema; tolerant, degrade-to-empty.

**Size:** M

**Files:** flowctl.py (parser functions - mind the dual-copy + SOURCE_SHA256 pin checklist), tests module.

### Approach
- Parse numbered finding blocks w/ labeled fields (Severity incl. P0-P3 mapping, Confidence anchors, Classification, File:Line -> file+line, Problem -> title/body split, Suggestion, R-ID mentions -> rIds[]); ratchet forms ("Prior finding N - fixed|not-fixed") -> status on prior-linked findings; ordinal preserved.
- Tolerance: unknown labels ignored; missing anchors leave file/line null; wholly unparseable -> [] (never raises); size-bounded input handling.
- Tests over the .1 corpus: every backend shape, edge cases, property: parser never throws on arbitrary text.
- Quick commands: focused unittest module.

## Acceptance
- [ ] Parser covers the corpus w/ degrade-to-empty + never-throws property (R2).
- [ ] Output matches the receipt findings schema exactly (R1).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

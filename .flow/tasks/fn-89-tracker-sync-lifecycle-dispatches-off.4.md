---
satisfies: [R12]
---

## Description

Live interleave proof + dogfood measurements.

**Size:** S
**Files:** none (evidence-only; task evidence + optionally a decision-record memory entry)

1. On a linked spec, run one REAL comment-shaped touchpoint through the new path: background dispatch, host does real work meanwhile, notification join, `sync check` clean (no false MISSING, no duplicate retro-fire), terminal line parsed from the LAST line.
2. Record measurements in evidence: runner tokens for the comment op, host-context lines added (should be ~2: dispatch + outcome), wall-clock overlap.
3. If any invariant wobbles (double retro-fire, unparseable line), STOP and file the finding - do not paper over.

## Acceptance
- [ ] R12: proof recorded with measurements; both MUST invariants held

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

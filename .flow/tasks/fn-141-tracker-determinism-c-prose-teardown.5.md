---
satisfies: [R14, R15]
---
# fn-141-tracker-determinism-c-prose-teardown.5 Re-freeze fn-130 tracker baselines with enumerated fixtures + delta

## Description
Re-freeze fn-130's reached-path B1 baselines for the tracker cluster, invalidated by design by R1's prose reduction.

**Enumerate every affected fixture by name** under `optimization/reached-path/fixtures/b1/tracker` rather than treating it as a blanket refresh, and record a before/after delta artifact in the honest form fn-134 used when its own change grew the path.

## Acceptance
- [ ] Every affected fixture enumerated by name
- [ ] Before/after delta recorded as an artifact
- [ ] Rationale recorded: reduction by design, not regression
- [ ] Reached-path harness green
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

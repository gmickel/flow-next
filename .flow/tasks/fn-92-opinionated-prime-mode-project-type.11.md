---
satisfies: [R19]
---

## Description
Non-CI agentic eval harness: judgment-layer classification eval with rubric + provenance.

**Size:** S | **Files:** `optimization/prime/` (runner, rubric, expectation rows, README)

## Approach
- Per the reveval/optimization precedent: a standalone harness that runs the SKILL's judgment layer (final five-axis values, confidence, R15 question quality, playbook selection) over the synthetic fixtures + captured real-repo metadata snapshots.
- Define: the runner invocation, model/version provenance capture, the pass rubric, and the blocking threshold (what must hold before ship - consumed by task 9).
- Real-repo baselines: sanitized metadata snapshots committed as fixture projections (never live-repo CI dependencies); provenance recorded per run.

## Key context
- Never claim prose-contract tests prove judgment (round-2 finding); this harness is the judgment oracle.

## Acceptance
- [ ] Runner + rubric + blocking threshold documented and executable locally
- [ ] Provenance (model/version/date) recorded in every result file
- [ ] Real-repo expectations run from committed sanitized snapshots, not live paths

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R19]
---

## Description
Emitter substance collectors + redaction + performance accounting + fixture families + CI oracle.

**Size:** M | **Files:** both flowctl copies (extend the task-4 framework), `plugins/flow-next/tests/test_prime_eval.py`, fixture-builder module

## Approach
- All emitter-owned rows of the resolution-21a ownership matrix (consumes task 1's map): hook classification inputs, env cross-ref counts, destructive-scan raw hits with context class, LEG5 encoding sampling, LEG6 atomic-pair candidates, LEG7 tool-managed/regenerated-dir candidates, docs-freshness timestamps, CI trigger + mutating-lint greps, secrets-gate config presence, API-contract globs, module-boundary/test-isolation/flaky/LLM-eval config presence.
- Redaction contract: key names only, never values or full sensitive lines; fixture asserts it.
- Performance accounting per resolution 21b: op-count assertions in CI (never wall time); generated high-file-count benchmark fixture; documented local wall-time benchmark vs the <10s target; timeout/progress failure assertions.
- Fixture families (temp git-init, never in-tree .git): workspace-parent, tier-a siblings, tier-b home base (asserts assessment_scope=constellation-home-base), greenfield, greenfield-x-constellation, worktree-sibling.
- CI oracle: per-row expectation table over raw signals/markers/exclusions/diagnostics only.

## Acceptance
- [ ] Every emitter-owned matrix row implemented with fixture coverage and completeness diagnostics
- [ ] Redaction fixture green; op-count bounds asserted in CI; benchmark fixture + local wall-time note
- [ ] Six fixture families + expectation rows pass 3-OS

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

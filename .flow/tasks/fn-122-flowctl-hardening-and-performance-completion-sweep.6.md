---
satisfies: [R11, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.6 Prime classifier performance pass

## Description
Optimize prime classify from the post-3.1.0 baseline. Precompute the lowercase tracked-path inventory once, remove repeated root realpath/containment work, and batch or safely parallelize independent Git probes. Reuse bounded metadata/content where semantics permit.

The unchanged code measured ~0.585s warm after previously measuring ~2.7s under different cache/load conditions, so repo wall time is not a reliable acceptance gate. Prove the algorithmic work with deterministic operation/subprocess counts and a Pascal-heavy synthetic fixture that exposes the current O(P×N) lowercasing path. Keep same-machine wall measurements as evidence.

Preserve file/read caps, classification output, evidence ordering, redaction, platform behavior, and failure isolation.

Complexity: 62/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_prime_classify test_prime_eval test_prime_substance -q
## Acceptance
- [ ] Pascal/Delphi atomic-pair detection is O(N), with the lowercase set built once.
- [ ] A Pascal-heavy synthetic fixture proves the operation-count/asymptotic improvement.
- [ ] Root realpath/containment work is cached without weakening traversal containment.
- [ ] Independent Git probe count/work is materially reduced without masking failures.
- [ ] Classification, evidence, caps, and redaction remain golden-fixture equivalent.
- [ ] Same-machine wall timing is reported as evidence, not a flaky acceptance threshold.
- [ ] Focused prime suites and deterministic operation-count tests pass.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

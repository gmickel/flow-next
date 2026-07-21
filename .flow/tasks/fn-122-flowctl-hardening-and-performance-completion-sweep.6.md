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
Optimized Prime classification without changing its JSON contract: Pascal/Delphi atomic-pair matching now builds one lowercase inventory; root realpath resolution is fingerprint-cached while every target containment check remains live; independent lifecycle/docs Git probes run concurrently with ordered, fail-soft sequential fallback; and streamed Git inventory always closes/reaps its process handles. Added deterministic asymptotic, containment-retarget, concurrency/fallback, and resource-cleanup tests.
## Evidence
- Commits: f75a17d6, 6b814891
- Tests: PATH=/opt/homebrew/bin:$PATH PYTHON_BIN=/opt/homebrew/bin/python3 /opt/homebrew/bin/python3 -m unittest test_prime_eval test_prime_performance test_startup_bootstrap test_hot_path_memoization -q (220 tests), Prime classify JSON SHA-256 matches pre-change output byte-for-byte, Prime classify warm median: 0.5742s before, 0.4758s after (10 runs after 2 warmups; 17.1% faster), flowctl codex impl-review --base e47ee9ac (round 2 SHIP)
- PRs:
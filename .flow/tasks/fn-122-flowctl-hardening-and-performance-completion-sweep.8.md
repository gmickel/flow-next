---
satisfies: [R13, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.8 Memory, pilot-log, and frontmatter performance pass

## Description
Parse memory frontmatter/body from one read buffer, add metadata-only iteration, resolve validated fully-qualified IDs directly, and choose/cache optional YAML parsing once per process. Keep ambiguous-slug scans and containment checks.

Replace pilot-log's cumulative O(N^2) tick allocation with lock-protected next-tick state and recovery from absent/corrupt counters. Centralize the frontmatter envelope while keeping strategy/memory/prospect schema coercion and their distinct absent/malformed sentinels.

Complexity: 72/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_memory_read test_memory_list test_memory_search test_pilot_log test_strategy test_prospect -q
## Acceptance
- [ ] Memory list/read/search use one content read per entry plus constant selected-target overhead.
- [ ] Fully-qualified memory IDs resolve directly with strict grammar and containment validation.
- [ ] Optional PyYAML and pure-stdlib fallbacks preserve schema-specific value/sentinel behavior.
- [ ] Pilot steady-state append reads O(1) historical rows and remains collision-safe under concurrency.
- [ ] Missing/corrupt pilot counter state reconstructs safely from rows.
- [ ] Frontmatter envelope dedupe does not collapse strategy/memory/prospect malformed/absent contracts.
- [ ] Focused suites and deterministic read-count tests pass.
## Done summary
Completed the memory, pilot-log, and frontmatter performance pass.

- Centralized schema-aware frontmatter envelopes and cached optional PyYAML selection while preserving strategy, memory, and prospect sentinel/coercion contracts.
- Reduced memory metadata/search iteration to one file read per entry, resolved validated full IDs directly in one read, separated body/raw retention, and rejected traversal, external symlinks, and symlink loops without tracebacks.
- Replaced pilot tick-history rescans with crash-safe per-ID counter state and deterministic recovery for absent, corrupt, stale-valid, crash-ahead, and orphan-reservation states.
- Preserved canonical/dogfood source identity and refreshed hash-validated bootstrap metadata.
- Addressed all findings emitted across four bounded implementation-review rounds. The final reviewer finding (symlink-loop RuntimeError) was fixed and regression-tested after the external review-round cap was exhausted; no reset or fabricated SHIP verdict was recorded.

Deterministic evidence: exact full-ID lookup dropped from 48 reads to 1 on the 24-entry fixture; metadata/search scans dropped from 2N to N reads; steady-state pilot tick 41 dropped from 40 historical-row reads to 1 commit-witness read. Live memory-list timing remained at a 0.19s median (no regression).
## Evidence
- Commits: ae9b5b4e, f30cc2d6, 1a7a3ae1, 589ba7a5
- Tests: cd plugins/flow-next/tests && PATH=/opt/homebrew/bin:$PATH PYTHON_BIN=/opt/homebrew/bin/python3 /opt/homebrew/bin/python3 -m unittest test_memory_performance test_memory_list_read_search test_memory_during_spec_null_safe test_frontmatter_performance test_pilot_log test_pilot_backlog_substrate test_startup_bootstrap -q (105 passed), canonical/dogfood flowctl.py cmp parity, git diff --check
- PRs:
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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

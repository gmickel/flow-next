---
satisfies: [R4, R16]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.3 Post-fn-121 model-resolution and cache reconciliation

## Description
Fix the model-resolution cache defects reconfirmed unchanged in flow-next 3.1.0.

The cache key remains backend@CLI-version and is consulted before the current non-explicit role-map ladder start. Fresh reproduction: requested role pin gpt-5.6-sol, cached gpt-5.5, actual dispatch gpt-5.5. Key/cache validation must incorporate effective routing intent. Define bounded expiry or controlled stronger-model re-probe for downgrade/floor entries so account/server availability can recover without a CLI upgrade.

Serialize cache put/invalidate read-modify-write operations so unrelated backend entries survive concurrent reviews. Preserve the full explicit precedence chain and ensure explicit models never silently downgrade. Retain fn-121's documented session-steering versus machinery-steering split; this task changes deterministic cache correctness, not routing policy.

Complexity: 70/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_model_resolution test_backend_spec test_config_snapshot -q
## Acceptance
- [ ] Effective role-map/routing intent participates in cache validity; a changed role pin cannot be masked by a stale downgrade.
- [ ] Downgrade/floor entries have tested expiry or controlled stronger-model re-probe behavior.
- [ ] Concurrent put/put and put/invalidate operations preserve unrelated backend keys.
- [ ] Explicit per-task/spec/env/config pins retain 3.1.0 semantics and never silently downgrade.
- [ ] Cached distinctive-signature failures remain self-healing without masking auth/network/other errors.
- [ ] Session-steering versus machinery-steering documentation remains true.
- [ ] Focused model-resolution and cache tests pass.
## Done summary
Made model-resolution caching intent-aware and bounded: cache identity now includes backend, CLI version, and routing intent; entries expire after 24 hours; malformed or stale signatures self-heal; and explicit pins continue to bypass auto-resolution. Serialized cache mutations preserve unrelated entries across concurrent puts and invalidations, while pruning obsolete same-backend keys to avoid growth and repeat probes.
## Evidence
- Commits: 85b414be, e3fae840
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_model_resolution test_backend_spec test_config_snapshot test_anchor_bundle test_pilot_backlog_substrate -q (292 tests passed), python3 -m py_compile plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py, cmp -s plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
- PRs:
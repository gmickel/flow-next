---
satisfies: [R1, R3]
---
# flow-98-remove-packaged-codex-delegation.1 Delete the delegation config keys, the role-map delegate pin, and the schema entries

## Description
Remove the six `work.delegate*` keys and the `models.roles.delegate` pin from the CLI, the published schema table, and the regenerated artifact. This is the deterministic half; the prose half follows in .2 so the two do not collide in one file.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (config reader/writer/validator paths for `work.delegate*` and the role-map `delegate` entry), `scripts/gen_flow_config_schema.py` (TABLE), `plugins/flow-next/schema/flow-config.schema.json` (regenerated, never hand-edited), `.flow/bin/flowctl.py` (propagated copy)
**Touches:** [plugins/flow-next/scripts/flowctl.py, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/flow-config.schema.json]

### Approach
- Re-grep the key names before editing; the six are `delegate`, `delegateConsent`, `delegateDecision`, `delegateEffort`, `delegateModel`, `delegateSandbox`.
- Reader/writer/validator paths go together. A key removed from the schema but still accepted by the reader is the drift the schema test exists to catch.
- `models.roles` keeps its shape; only the `delegate` role and its per-backend pins go. The rest of the role map is the successor spec's problem, not this task's.
- Regenerate the schema artifact with the generator; never hand-edit it. Keep the drift test green.
- **The removed-key advisory belongs here, with the deletion:** a config still carrying any of the six keys gets one actionable line naming the key and pointing at the routing preference plus the bridge recipe, and never blocks. One line per invocation, not per key and not per phase.
- Do NOT propagate here: the dogfood copies, the manifest and the mirror all belong to the close-out task. Touching `.flow/` would make this task always-serial and cost the wave.

### Investigation targets
**Required** (read before coding):
- the config get/set/validate paths in the CLI for `work.*` - the exact shape a removed key must produce
- `scripts/gen_flow_config_schema.py` TABLE - the source of truth for the published schema
- `plugins/flow-next/tests/test_flow_config_schema_drift.py` - what green means here

### Acceptance
- [ ] All six `work.delegate*` keys gone from reader, writer, validator and schema TABLE; regenerated artifact matches
- [ ] `models.roles.delegate` gone; the remaining role entries untouched
- [ ] A config carrying any removed key produces one actionable advisory and runs unchanged; no blocking, no repetition per key
- [ ] Schema-drift test green
- [ ] Propagation (module copy to the dogfood bin, manifest regen, mirror sync) is NOT done here - it belongs to the close-out task so this one stays wave-eligible
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_work_delegate_config test_model_resolution -q` (the delegate-specific file is deleted in .4; expect it red here and say so)

## Acceptance
- [ ] TBD

## Done summary
Removed the six `work.delegate*` config keys (whole top-level `work.*` namespace) and the `models.roles.delegate` pin from flowctl, the schema-generator TABLE, and the regenerated `flow-config.schema.json`. A config still carrying any removed key gets one non-blocking stderr advisory line (per process, latched) naming the keys and pointing at the /flow-next:setup model-routing scaffold + .flow/usage.md bridge recipes; wired at config get/set, anchor, brief. New test file test_removed_delegate_config_advisory.py; namespace-coexistence assertions repointed off work.* in four sibling test files.

Deferred by design: propagation (.flow/bin, tracker manifest, codex mirror) → task .5; test_work_delegate_config.py deletion → task .4.

Implemented in isolated worktree (wt/flow-98.1, c194dec7), integrated onto spec branch as 88ca14e3.

stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.1.json)
stage: delegation - skipped(config: delegation off)stage: plan-sync - ran (drift: no; downstream .3/.4/.5 unchanged; cross-spec check not run in subagent - covered by conductor before .5)

## Evidence
- Commits: 88ca14e3ef868c8ea02b8338eed4b49a84804d1f
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_model_resolution test_removed_delegate_config_advisory -q (107 tests OK, worker worktree), integrated verify @88ca14e3+.2: cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_model_resolution test_removed_delegate_config_advisory test_work_reached_path_routes test_parallel_work_prose test_foreground_rule_fences -q (121 tests OK), uvx ruff@0.16.0 check . (All checks passed, integrated tree), python3 scripts/run_tests_parallel.py (worker worktree) -> failures ALL owned by deferrals: test_work_delegate_config (.4), dogfood/manifest/mirror propagation (.5), impl-review: host backend SHIP (reviewer claude-fable-5, fresh read-only subagent; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.1.json)
- PRs:
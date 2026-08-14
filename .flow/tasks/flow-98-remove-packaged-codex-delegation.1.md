---
satisfies: [R1, R3]
---
# flow-98-remove-packaged-codex-delegation.1 Delete the delegation config keys, the role-map delegate pin, and the schema entries

## Description
Remove the six `work.delegate*` keys and the `models.roles.delegate` pin from the CLI, the published schema table, and the regenerated artifact. This is the deterministic half; the prose half follows in .2 so the two do not collide in one file.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (config reader/writer/validator paths for `work.delegate*` and the role-map `delegate` entry), `scripts/gen_flow_config_schema.py` (TABLE), `plugins/flow-next/schema/flow-config.schema.json` (regenerated, never hand-edited), `.flow/bin/flowctl.py` (propagated copy)
**Touches:** [plugins/flow-next/scripts/flowctl.py, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/flow-config.schema.json, .flow/bin/flowctl.py, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, .flow/bin/flowctl_tracker/MANIFEST.json]

### Approach
- Re-grep the key names before editing; the six are `delegate`, `delegateConsent`, `delegateDecision`, `delegateEffort`, `delegateModel`, `delegateSandbox`.
- Reader/writer/validator paths go together. A key removed from the schema but still accepted by the reader is the drift the schema test exists to catch.
- `models.roles` keeps its shape; only the `delegate` role and its per-backend pins go. The rest of the role map is the successor spec's problem, not this task's.
- Regenerate the schema artifact with the generator; never hand-edit it. Keep the drift test green.
- Propagate per the project instruction file: copy the module to the dogfood bin, regenerate the manifest, run the mirror sync twice.

### Investigation targets
**Required** (read before coding):
- the config get/set/validate paths in the CLI for `work.*` - the exact shape a removed key must produce
- `scripts/gen_flow_config_schema.py` TABLE - the source of truth for the published schema
- `plugins/flow-next/tests/test_flow_config_schema_drift.py` - what green means here

### Acceptance
- [ ] All six `work.delegate*` keys gone from reader, writer, validator and schema TABLE; regenerated artifact matches
- [ ] `models.roles.delegate` gone; the remaining role entries untouched
- [ ] Schema-drift test green; propagation done (module copy, manifest regen, mirror sync x2) and the tree clean
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_work_delegate_config test_model_resolution -q` (the delegate-specific file is deleted in .4; expect it red here and say so)

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

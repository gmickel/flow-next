# fn-115-model-pin-registry-role-map-in-config.1 Role-map config + resolution order + staleness nudge

## Description
Role-map config plumbing: models.roles namespace, resolution order, verifiedAt staleness nudge.

**Size:** M
**Files:** both flowctl.py copies, tests

### Approach

- Read the fn-115 spec design sketch fully. Add the config namespace models.roles.<role>.<backend> for ONLY the roles that exist today: fastJudge, review, delegate, scoutFast, scoutIntelligent; plus models.verifiedAt (ISO date) and optional models.verifiedWith. Schema validation on flowctl config set (unknown role/backend rejected with the valid list).
- Resolution order extends the existing fn-76 precedence exactly: explicit CLI flag / per-task pin > env > config role map > registry baseline. Registry ladders REMAIN as availability fallbacks (they heal pin-too-new; the role map heals pin-too-old).
- Wire consumers: triage judge reads fastJudge (re-homes fn-113.1's interim gpt-5.6-luna/high default - the hardcoded default becomes the registry baseline under the role map), review-backend dispatch default reads review, work.delegateModel default reads delegate. Deep-pass/validator ride the review resolution as today.
- Staleness nudge: mechanical date check ONLY - when models.verifiedAt is older than ~90 days, setup/status print one line (model pins last verified <date>; re-run setup to refresh). Never blocks, never judges, absent verifiedAt = no nudge (fresh repos).
- NO probing, NO model judgment, NO LLM calls in Python - the ceremony (task 2) owns intelligence.
- Tests: resolution-order matrix per consumer (explicit/env/role-map/baseline), schema rejection, nudge date math, verifiedAt round-trip. Dual-copy; sync-codex x2 if needed. NO git commands, no flowctl start/done, no em dashes.

### Acceptance

- [ ] models.roles + verifiedAt validated on set; resolution order proven per consumer by tests
- [ ] fastJudge role feeds the triage judge (fn-113 default becomes baseline); review/delegate roles feed their consumers
- [ ] Nudge fires only past ~90d, one line, never blocks
- [ ] Focused: test_model_resolution.py + test_backend_spec.py + test_gate_classify.py green; dual-copy identical

## Acceptance
- [ ] TBD

## Done summary
Role-map plumbing complete: models.roles.<role>.<backend> config namespace for exactly the five live roles, schema-validated on set (unknown role/backend/leaf errors with the valid list; pins are model or model:effort; verifiedAt ISO-validated). Resolution extends the fn-76 precedence in place per consumer: review (dispatch + deep-pass + validator ride BackendSpec.resolve model-fill), fastJudge (triage judges; fn-113's gpt-5.6-luna@high re-homed as the registry baseline under the map), delegate (raw on-disk work.delegateModel beats map; merged default alone does not), scout roles stored+validated for .3 consumption. Staleness nudge is pure date math (MODELS_STALE_DAYS=90, quiet when absent/unparseable, one line in status when stale, never blocks). No probing, no judgment, no LLM calls in Python - doctrine boundary held. 58 resolution/schema/nudge tests. Delegate-skill read path (doubt 1) assigned to .3 wire-in: a thin read-only models resolve surface so the work skill consumes the map instead of the merged default. Full parallel suite 89 files / 1921 tests / 0 failures / 71.4s; dual-copy identical.
## Evidence
- Commits: f871b3f1883f1e78f76ff4d2f33d7c437dffd5b0
- Tests: python3 scripts/run_tests_parallel.py (89 files, 1921 tests, 0 failures, 71.4s), test_model_resolution.py 58 green (matrices, schema, nudge), test_backend_spec 144 / test_gate_classify 18 green
- PRs:
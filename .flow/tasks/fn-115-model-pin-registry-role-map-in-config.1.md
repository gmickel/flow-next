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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

# fn-115-model-pin-registry-role-map-in-config.3 Scout-pin consumption + docs + rider + full gate

## Description
Scout-pin consumption + docs + CHANGELOG rider + full gate.

**Size:** S
**Files:** scripts/sync-codex.sh, plugins/flow-next/docs/orchestration.md + docs/flowctl.md, CHANGELOG.md

### Approach

- sync-codex.sh: the CODEX_MODEL_INTELLIGENT/CODEX_MODEL_FAST scout-tier pins read from the role map when the repo config carries scoutFast/scoutIntelligent (env override still wins; baseline unchanged when absent) - mirror-regen time only, no runtime coupling.
- Docs: flowctl.md config-section documents models.roles/verifiedAt + resolution order; orchestration.md explains the role map as the one place pins rot and the ceremony as the refresh path.
- CHANGELOG [Unreleased] rider for the whole fn-115 spec.
- Full gate: full parallel suite + smoke_test.sh + ci_test.sh (host re-runs).

### Acceptance

- [ ] sync-codex consumes role-map scout pins (env wins; absent = baseline); regen x2 idempotent
- [ ] Docs + rider present; full suite + smokes green

## Acceptance
- [ ] TBD

## Done summary
Scout-pin consumption: sync-codex.sh reads models.roles.scoutFast/scoutIntelligent.codex from repo config at mirror-regen time (env override wins; absent map = unchanged baselines; model id only, effort stripped), regen x2 idempotent. The one sanctioned new command: flowctl models resolve <role> [--backend] [--json] - pure map+precedence lookup through the existing resolvers, added because the work skill read config get work.delegateModel whose merged default bypassed the role map; the delegate callsite now consumes models resolve delegate. Docs: flowctl.md (config namespace, resolution order, resolve command), orchestration.md (role map as the single rot point + ceremony as the refresh). Consolidated CHANGELOG rider covers all three tasks. Final gates: full parallel suite 90 files / 1930 tests / 0 failures; smoke_test.sh 136/136 (first run failed on a machine-wide mise/codex shim drift - "No version is set for shim: codex" - reproduced independently of our diff and green with a scoped MISE_NODE_VERSION pin; environment finding surfaced to maintainer, not a code issue); ci_test.sh 67/67; test_model_resolution 65; dual-copy identical; sync-codex x2.
## Evidence
- Commits: 315649e57b86d2bf7366e20fd5223c92333d0958
- Tests: python3 scripts/run_tests_parallel.py (90 files, 1930 tests, 0 failures), MISE_NODE_VERSION-scoped smoke_test.sh 136/136 (env drift documented), bash ci_test.sh (67/67), test_model_resolution.py 65 green, live: flowctl models resolve delegate -> gpt-5.6-terra source=config
- PRs:
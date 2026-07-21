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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

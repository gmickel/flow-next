---
satisfies: [R6]
---
# fn-178-stage-receipts-ran-skipped-failed.2 CHANGELOG Unreleased entry (stage receipts)

## Description
Extend the Unreleased CHANGELOG with the fn-178 entry.

**Size:** S
**Files:** `CHANGELOG.md`
**Touches:** [CHANGELOG.md]

### Approach
- Bullet under `## Unreleased` > `### Changed`: pipeline stages now leave an explicit outcome (ran / skipped with reason / failed with reason) in the receipts they already write, so a silently no-oping stage (the #293 class) is visible on first occurrence; `flowctl usage --stages <spec>` summarizes them. No new stores; token telemetry explicitly out of scope.
- No version bump. Done summary notes docs-site owed at batched release.

### Acceptance
- [ ] Unreleased bullet present, no em dashes
- [ ] No version manifests touched
- [ ] Done summary notes docs-site owed at batched release

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

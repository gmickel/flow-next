---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-331-tracker-rejections-say-why-and-idea.1 Implement Tracker rejections say why, and idea text reads clean

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Jira and GitLab client-error rejections keep `rejected (<status>)` and append the tracker's own reason from the response body (Jira `errorMessages` and `errors` as `field: text`; GitLab `message` / `error` as a string, list or map of lists), redacted before a 200-character cut; class and subtype unchanged; GitHub and Linear untouched. On GitLab's glab route the classifier now gets glab's stdout when it is a JSON object, and glab's stored token for the target host is registered for redaction. `flowctl tracker idea read` strips Jira colour tags from idea bodies and comments; the ordinary issue read and every write are unchanged. Docs: changelog Unreleased/Fixed, tracker-sync parent-rejection paragraph. Live: Jira Cloud wrong-level parent and GitLab too-long title both show the reason and created nothing; template idea read has no colour tags while the wire read is unchanged from 9.13.0.

stage: impl-review - ran [round 1 NEEDS_WORK (3 findings fixed) .. round 2 SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: d8ab1c906efae05682eea8419e3d45a617c35958, 529d3a34e66c9e287807db5cc17355e4bbd4275a, cadbe05cc613599f111a64b4f11a789f33a9b66d, 6b139e67f767ab810f2bef8dfd68ddea0bf2cdf6, e98f123abb9395ed2b27c4aaef52ab16553f80e3
- Tests: python3 -m unittest (tracker suites: tests/test_tracker_*.py, test_land_tracker_api, test_chart_tracker_projection) - 1194 OK
- PRs:
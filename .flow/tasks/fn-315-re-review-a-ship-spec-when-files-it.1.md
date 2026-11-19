---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-315-re-review-a-ship-spec-when-files-it.1 Implement Re-review a SHIP spec when files it cites changed before work starts

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
A SHIP plan review whose tasks are all still `todo` now routes back to `plan_review` when a backtick-cited repo path (outside `.flow/`) changed between the commit the review observed and HEAD. One helper, `plan_review_drift`, serves the route judge, the pilot snapshot and `flowctl show --json` (`plan_review_drift`); direct work prints one note and continues (work phases.md, conduct checklist). Drift is derived on read: the next SHIP clears it.

Review fixes: superseded late verdicts are skipped; only a commit observed before dispatch counts, and plan reservations now store HEAD so host reviews carry one; a reviewed commit on no branch or tag and not behind HEAD is no drift; `./.flow` is excluded; git output is read as bytes.

Declined: a behavioural test of the direct-work note (skill prose; G2 bans prose assertions; R7's enumerated fixtures are covered).

stage: impl-review - ran [round 1 three lenses NEEDS_WORK .. round 4 SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 0dd226cba53048ae2a80a05f5e0eb830aa5fdef0, 2564fa7b0ec89048242eb978796180493b51e625, f1e2bf2e09cf380bd24ea4c92c3cd933f2b27f05, bb8276ab2998b25fd3654e79ab1128b554678b5e, 1cbd4409554f529dfd96b3d8c33f325cac89454a
- Tests: python3 -m unittest test_plan_review_drift test_judge_route test_pilot_snapshot test_review_convergence_journal test_review_convergence_cap test_host_review_backend (331 OK), python3 -m unittest <20 caller suites> (479 OK)
- PRs:
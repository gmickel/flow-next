---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-344-9180-last-fixes-legacy-fan-out-rows.1 Implement 9.18.0 last fixes: legacy fan-out rows, criteria section end

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
R1: finalize applies the same-label rule only when the primary's label is known, so a 9.17.0 pending row keeps 9.17.0's survivor; a session-less survivor still stamps its label; a legacy round with no command survivor is refused (nothing recorded, re-dispatch).
R2: the criteria section ends at a tally line (bold/quote markers and spacing as the tally parser accepts) or at a fenced JSON tally block closed by a bare fence line; any other fence stays ambiguous.
R3: the documented agy wrapper (and Codex mirror) passes --print-timeout 5s before its own subprocess stop, never under 1s.
R4: Antigravity setup's no-CLI note ends "or choose None"; its More backends follow-up no longer offers Host (platform guide, checklist updated).
R5: saved "CLAUDE.md only" with no CLAUDE.md snippet now reports the missing snippet (reproduced by trace, fixed); the skill-id snippet observation did not reproduce (fn-341 chose hidden stubs; model reads skill ids), left alone.
stage: impl-review - ran [round 1 fan-out (1 draw) .. round 4 SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: a667156993cde7f1bb2ae54cfaddabaa5f2d6414, e793eddc001c3b0a27da7cc4c4795d4c301a8ff4, 10ef22b4370793c48ace6f817e7fa78ab452efeb, e87377e807efb372e60698cd2297600ef9eb0920, 774df72cf2b9bef0f41e934aafc2eee90818ca27, 6ee8e822d427c0f2a6d9e98676e02c53cd036a73, 9c786335664eb62e707d1b364ce4c816e65c8e13, 59b0f01480bb7b1d2da49f073c95e9c9d4ba74fa, 1ed3b788fff823bcdf8c015f3958ee1999279df5, 1324902023a90ca328f97eee7607da08e628cece, 7dce0b0846c322697578a9998fc1270bbd92b2d3, dd989e9ae61a9c6c02ee75b49ab73fc049964e75, d4b124a1258d555c8e604cfa5856425d3bd96d01, 1499516740d8318d02b6642ed01a04fc809bf7d4, 67449462ffeb94b0929e4b21b5b7a085d156c86b
- Tests: python3 -m unittest tests.test_criteria tests.test_command_review_backend tests.test_review_fanout tests.test_claude_review_commands tests.test_review_convergence_cap tests.test_review_convergence_journal tests.test_review_findings_model_shapes tests.test_setup_grok_host tests.test_setup_spec_discovery_hits tests.test_install_antigravity
- PRs:
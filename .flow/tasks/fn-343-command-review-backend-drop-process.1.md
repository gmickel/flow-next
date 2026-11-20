---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-343-command-review-backend-drop-process.1 Implement Command review backend: drop process-tree management

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Command reviews are back on 9.17.0's process handling. One child runs in flowctl's
process group and is killed directly on a timeout or an oversized response. Fan-out
draws are back on the 9.17.0 executor. The process-tree stop helpers, the interrupt
registry, the background-thread fan-out and its wait bounds are gone, and so are the
nine tests that covered only them.

The docs, the mirror and the changelog now say that flowctl stops only the program it
started. A wrapper must pass the timeout on, with a deadline earlier than flowctl's, and
must not detach what it runs. Ctrl-C reaches the wrapper's children only while they stay
in its process group.

Fixes kept or added:
- Pending fan-out rows record the command label (R5).
- Retired Copilot ids are back at the ladder's tail (R6).
- The agy wrapper reads `agy` from an absolute `AGY_PATH` and does no PATH lookup (R4).
- fn-339 R3 and fn-342 R3/R4 are marked withdrawn (R7).

New tests:
- A live SIGINT to flowctl's process group, for single and fan-out runs on the command
  and codex backends (R2).
- A stalled agy under a short budget.
- Interrupted fan-out recovery, for same-label and different-label survivors.
- Legacy decoding of retired Copilot dash specs.

Declined #1: re-adding a checkout-containment check for AGY_PATH. The spec's Decision
Context rules it out, and the docs now tell users to point AGY_PATH at the installed agy.

stage: impl-review - ran [round 1 NEEDS_WORK (3 draws), re-review SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 07a57f7975a587f886aa4c199c38f826e5ff6165, 12786e12919ade43ca652090388d075b2c519ec3, 698dd197b67f9a6d79a9b374e87188778d76a624
- Tests: python3 -m unittest test_command_review_backend test_review_fanout test_backend_spec test_criteria; uvx ruff@0.16.0 check .
- PRs:
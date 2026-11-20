---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-339-follow-ups-from-the-criteria-and.1 Implement Follow-ups from the criteria and command-backend work

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Fixed the ten follow-ups in flowctl, setup and plan prose, docs and tests.

- R1: a `.flow/criteria.md` that git's index records as a symlink (mode 120000) but the checkout holds as a plain file fails closed in `criteria list`, `criteria prompt-block` and every review prompt build; other zero-criteria files stay valid.
- R2: reproduced from the codex reviewer output that dropped the criteria (fn-336 round 2); a tally line or fenced tally block now ends the `## Global criteria` section.
- R3: a timed-out or oversized command review kills its process group plus descendants that left it (POSIX), or `taskkill /T` (Windows); an unstoppable tree is named in the reason; fully detached processes are documented as not stopped.
- R4: `config set review.backend` refuses a command spec without a label; an unset label variable is still accepted.
- R5: not run: copilot returned "You have exceeded your monthly quota" on one completion-review call (request 00000-9ecd97f0-bf63-4557-a093-c34caf37808d); the teams guide keeps "unchecked".
- R6: missing/unrunnable program errors name FLOW_REVIEW_COMMAND_<LABEL> and the label, not the path.
- R7: fan-out fallback keeps the primary draw's command label; with no session there the passes do not run.
- R8: whitespace in a command spec is refused by the parser, FLOW_REVIEW_BACKEND and --draw, as by the schema.
- R9: setup on Muse (list form, one word to add antigravity) reports a saved CLAUDE.md-only answer the host will not see.
- R10: plan's memory reference renders one line for uninitialized memory.

stage: impl-review - ran [round 1 three-lens NEEDS_WORK, round 2 NEEDS_WORK, round 3 NEEDS_WORK] (model: gpt-6.2-sol)
OPEN_ITEM: R7 - should command --validate/--deep start a fresh session on the primary label when it has none (new session-less pass), or not run as built? Left for the maintainer.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 3ab1869a125d0a22cc78913a1942621b8286a186, 393f6909af98e8bf82561095da0c545c38e34b89, 12d3356db1d9e021112cacf10069a93862c30d92, 5039829cbba860f4a664edc6e51c8074a6be15bd, ef0a50e7f9488b274e8e25f74bb1a7663b07df3c
- Tests: python3 -m unittest test_criteria test_command_review_backend test_backend_spec test_review_fanout (315 OK); focused callers (635 OK)
- PRs:
---
satisfies: [R12]
---
# fn-326-9110-pre-release-fixes-for-issue-start.5 End-to-end issue start on the final code

## Description
Headless flow --auto --from-issue <key> --until=merge on gmickel/flow-next-e2e-scratch (Linear FLOW, readyState Todo) with this branch's plugin: one clear issue (implementation review must run), and one refused -> plain answer -> follow-up question -> answer -> build. Isolated CLAUDE_CONFIG_DIR with a copied .credentials.json, deleted afterwards. Issues titled [fn-326 e2e] ..., done or canceled afterwards.

## Acceptance
R12 holds: both runs pass on the final code, PRs merged on the scratch repo, implementation review ran on each work hop.

## Done summary
Headless flow --auto --from-issue <key> --until=merge on gmickel/flow-next-e2e-scratch with this branch's plugin (isolated CLAUDE_CONFIG_DIR, copied credentials removed after each run).

- FLOW-125 (clear: add modulo): capture -> plan-review SHIP -> work (impl-review SHIP, ran under the new always-review rule) -> make-pr #5 -> land MERGED 8a77616; FLOW-125 Done. No status conflict at the capture push (R6); the PR carries 'chore(flow): tracker sync state' and the link reached main (R13); checkout back on a clean main (R11).
- FLOW-126 (vague: rounding helper): run 1 ASKED with 5 questions, issue moved to Backlog, nothing written. Plain partial answer + back to Todo: run 2 posted a follow-up as a new round (question id aa8513cd vs 6100f2ed) and ASKED again (R3). Full answer + back to Todo: run 3 captured, plan-review SHIP, work with impl-review that caught a real Decimal precision crash (fixed with a regression test), make-pr #6, land MERGED fb2a85b; FLOW-126 Done.

stage: impl-review - skipped(policy: verification task, no code change)
Run by the conductor (claude-opus-5-5); headless children on the session's default model.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits:
- Tests: headless flow --auto --from-issue FLOW-125/FLOW-126 --until=merge on gmickel/flow-next-e2e-scratch (scratch PRs #5, #6)
- PRs:
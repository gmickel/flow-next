---
satisfies: [R2, R3, R4, R5]
---
# fn-188-land-opt-in-repo-merge-verdict-command.2 land workflow §2.9 merge-verdict gate + SKILL bullet + static workflow tests + conduct item

## Description
R2/R3/R4/R5 - In plugins/flow-next/skills/flow-next-land/workflow.md: add '### 2.9 - Repo merge-verdict gate (opt-in, fail-closed)' AFTER 2.8 (~:383-388) and BEFORE the dry-run stop (~:390-392), modeled on 2.5b's prose shape (~:274-293: a why-paragraph, the wrong-tree warning, a verdict table, and a 'has broken this' invariant sentence). Contract to write into the section: reached only when every other gate is satisfied and the planned action is merge; command = the lcfg-captured land.mergeVerdictCommand string run via bash -c with cwd REPO_ROOT on ORIG_BRANCH; context arrives as environment ONLY - FLOW_HEAD_SHA (the .headRefOid already captured ~:194), FLOW_BASE_REF, FLOW_PR_NUMBER, FLOW_SPEC_ID - the configured string is never interpolated with PR-derived text; exit 0 = green -> proceed to merge; any non-zero = verdict NEEDS_HUMAN, action none (NOT BLOCKED - that class is reserved for server-side merge refusals ~:496), reason 'merge-verdict command refused (exit <n>): <last stderr line, ~200 chars>'; fail-closed set: configured-but-missing/unexecutable (127), timeout (600s, stated), signal death - all block, never skip; wrong-tree warning: the command runs on the base checkout, must key on $FLOW_HEAD_SHA and refuse when it cannot see that head - land does not check out the PR branch; off states: unset/null/"" all OFF; no needs-human label on refusal (matches 2.5b posture). --dry-run (R3): never executes the command - the classification report states 'would-run: <command>' (mirror the reviewTrigger dry-run treatment ~:357). Phase 0: add the one-line read off the EXISTING lcfg subtree capture (~:64-84) - test_skill_prose_diet.py:77-95 asserts exactly ONE config get call in the whole workflow; do not add a probe. Phase 4 evidence block (~:606-611): add mergeVerdict=<green|refused|skipped|would-run>. SKILL.md ~:109-110: one sub-bullet mirroring the cleanReviewCommentPattern bullet. R4 - static workflow assertions in test_land_config.py's CommentScanWorkflowStaticTestCase style (~:340-382): gate section present, fail-closed branch present, dry-run would-run branch present, env var names present, exactly-one-config-get preserved (run test_skill_prose_diet). R5 - one checklist item in agent_docs/conduct/land.md: 'When land.mergeVerdictCommand is set, no merge happens without a zero exit from it; a missing, unexecutable, or timed-out command blocks and never skips; --dry-run reports would-run and executes nothing.' Run ./scripts/sync-codex.sh twice and commit the mirror diff with your change. Plain hyphens, no em dashes.

## Acceptance
R2-R5 met; test_land_config + test_skill_prose_diet green; sync-codex idempotent; conduct item added.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

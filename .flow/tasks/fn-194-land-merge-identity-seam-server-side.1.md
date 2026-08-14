---
satisfies: [R1]
---
# fn-194-land-merge-identity-seam-server-side.1 FLOW_PR_MERGE_CMD seam at §3.5 with the stderr/no-auto contract

## Description
R1 in plugins/flow-next/skills/flow-next-land/workflow.md: the §3.5 merge call (~:568, `gh pr merge "$PR_NUMBER" --squash --delete-branch --match-head-commit "$HEAD_OID"`) honors FLOW_PR_MERGE_CMD: `MERGE_CMD="${FLOW_PR_MERGE_CMD:-gh pr merge}"` then `$MERGE_CMD "$PR_NUMBER" --squash --delete-branch --match-head-commit "$HEAD_OID"` with the existing stderr-only capture unchanged. Unquoted expansion (whitespace-split, never eval'd) - the exact FLOW_PR_CREATE_CMD shape from make-pr's create-and-finalize.md:271-305; read that first. Add an inline contract block (~12 lines) at the seam: fixed argument order; exit 0 = merged; the wrapper MUST proxy gh's stderr verbatim (3.5's RESOLVING-vs-BLOCKED classification at ~:577 reads gh's head-mismatch stderr text - a wrapper that eats stderr converts benign races into BLOCKED); never --auto or merge-queue enrollment; scope is the merge call ONLY (gh pr ready, the post-merge mergeCommit read, the tail, and every other gh call stay on the session identity); note --delete-branch needs a second permission a merge-only App may lack. Docs: docs/README.md bullet + docs/skills.md land row listing FLOW_PR_MERGE_CMD next to FLOW_PR_CREATE_CMD (match that listing's style). NO config key - env only (fn-188's trust guard is the argument: config-sourced command strings are PR-author-influenceable, session env is not). Static test in tests/test_land_config.py's workflow class: seam token pins (FLOW_PR_MERGE_CMD, the fallback default, --match-head-commit in the seam call, absence of --auto). sync-codex.sh x2, commit the mirror diff. Gate BARE: cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet -q.

## Acceptance
R1 met; seam mirrors the #277 shape; contract block states stderr-proxy + no-auto + merge-call-only scope; docs rows added; tests green; sync-codex idempotent.

## Done summary
§3.5 merge call honors FLOW_PR_MERGE_CMD (default gh pr merge) with the #277-shape unquoted expansion and a STABLE inline contract: fixed argument order, exit-0-merged, stderr proxied VERBATIM (the RESOLVING/BLOCKED split reads gh's head-mismatch text), never --auto/merge-queue, merge-call-only scope, --delete-branch second-permission note, env-only-never-config rationale citing §2.9's trust guard. Docs + conduct rows; 7 static pins. 79 tests green.
## Evidence
- Commits: 3b782ff3
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet -q
- PRs:
---
satisfies: [R13]
---
# fn-326-9110-pre-release-fixes-for-issue-start.6 make-pr commits and pushes the tracker sync state it writes

## Description
make-pr's tracker step (skills/flow-next-make-pr/tracker-finalize.md) writes sync state, and for an unlinked spec the tracker link it creates, into .flow/specs/<spec>.json after the PR push; that write never reaches the PR or main, so land's Done step (reads the PR head's spec) misses a link make-pr created and a later sync can duplicate the issue. Commit that JSON alone and push it to the PR head branch after the tracker call; a failed push warns.

Touches: plugins/flow-next/skills/flow-next-make-pr/tracker-finalize.md, plugins/flow-next/codex/skills/flow-next-make-pr/tracker-finalize.md, plugins/flow-next/tests/test_tracker_caller_execution.py, agent_docs/conduct/make-pr.md

## Acceptance
R13 holds: a fence test shows the changed spec JSON committed alone and on the PR branch, and no commit when it is unchanged; task 5's e2e run shows it live.

## Done summary
make-pr's tracker step now commits the spec JSON it wrote after the PR push (sync state, or a link it created for an unlinked spec) alone and pushes it to the PR branch; a failed push warns. Fence in skills/flow-next-make-pr/tracker-finalize.md, conduct line in agent_docs/conduct/make-pr.md.

Tests: test_tracker_caller_execution MakePrPushesTrackerSyncState (changed -> committed alone and on origin; unchanged -> no commit; from a subdirectory), failing first (8c7e981fc, b43b252bf), passing after (a6b36686a, f54dbac2f). Live: task 5's e2e run.

stage: impl-review - ran codex single reviewer NEEDS_WORK (1 finding: relative path from a subdirectory) then re-review SHIP (model: gpt-6.1-sol)
stage: plan-sync - skipped(config: planSync.enabled=false)
Implemented inline by the conductor (claude-opus-5-5).
## Evidence
- Commits: 8c7e981fc7584fbeb1b0b6176b42c6f09df9767b, a6b36686a82147f371bccff7e98e2050d4183ac9, b43b252bfc9a9c2913f868c3e5ccacc80ee4f27b, f54dbac2f72ed0dcc368e671191756fb3af53fa6
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker_caller_execution.py' (+ make_pr_gitlab, make_pr_bitbucket, make_pr_close, make_pr_reached_path, bundled_make_pr, make_pr_preflight_auth, flowctl_surface, ci_trigger_coverage)
- PRs:
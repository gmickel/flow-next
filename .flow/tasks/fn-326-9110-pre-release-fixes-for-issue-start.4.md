---
satisfies: [R11]
---
# fn-326-9110-pre-release-fixes-for-issue-start.4 --auto post-merge checkout state: fix or prove harmless

## Description
After an --auto run merges its PR (land with --delete-branch), the checkout stays on the merged, remote-deleted spec branch with one sync-state file changed (seen on every gmickel/flow-next-e2e-scratch run). Establish from auto.md, the snapshot fence and land whether the next --auto run misroutes from that state (wrong base, dirty-tree stop, stale spec). If it does, fix the smallest place (likely auto.md's post-merge step: return to the default branch's remote head, keeping the sync-state write committed or discarded deliberately). If not, record why with evidence. Runs after task 1 because both edit auto.md.

Touches: plugins/flow-next/skills/flow-next-flow/auto.md, plugins/flow-next/codex/skills/flow-next-flow/auto.md, plugins/flow-next/tests/test_flow_auto.py, agent_docs/conduct/flow.md

## Acceptance
R11 holds: the finding states fixed or harmless, with the evidence (a test or a recorded next run).

## Done summary
R11 finding: fixed. The post-merge state did misroute the next run, though not by wrong base or a dirty-tree stop. auto.md now leaves the checkout on the default branch at its remote head after a confirmed merge.

Tier: session (jev moderate 0.45) at default effort (model: claude-opus-5-5)

What the next run did from the old state (measured, disposable bare-repo reproduction, ~/.cache/agent-work/fn326-t4-repro/repro.sh):
- Wrong base: no. Issue start step 5 branches from the default branch's remote head, and work's `--branch=new` fence branches from the refreshed origin default.
- Dirty-tree stop: no. `pilot snapshot`'s `guards.dirty` skips `.flow/` paths, so the changed spec JSON passes the guard.
- Misroute: yes. The changed `.flow/specs/<merged-spec>.json` (make-pr's tracker reconcile writes it after its push, so the PR never carries it) rides `git checkout -b <next> origin/main`. The worker then stages it with `git add -- <files> .flow/`. Base run output, "files fn-2-b's PR carries": `.flow/specs/fn-1-a.json`, `.flow/specs/fn-2-b.json`, `src/a.txt`. So the next pull request carries the previous spec's sync state. A driver's `git checkout main` was also refused: "Your local changes to the following files would be overwritten by checkout: .flow/specs/fn-1-a.json".
- Head run with the fence: `Post-merge checkout: main at <sha>`, the tree is clean, and the next PR carries only `.flow/specs/fn-2-b.json` and `src/a.txt`.

The fix (b790713bf): auto.md Phase 6 has a new `fence:post-merge-checkout`. It runs before the terminal line of a run that confirmed a merge, and only when the checkout is on the merged spec's branch. Spec id and branch come from the persisted snapshot. The fence commits the spec JSON on the local spec branch as `chore(flow): tracker sync state for <id> after merge`. That commit is kept and never pushed. This is a deliberate choice over discarding: the JSON can hold the tracker link make-pr created, and `.flow` changes are not thrown away unattended. The fence then fetches and fast-forwards the default branch. Any other change, or any failed step, leaves the checkout where it is and prints what kept it. The merge verdict is unchanged. Goal mode does not read Phase 6, so it is unaffected. The Codex mirror is synced (21 agents). The agent_docs/conduct/flow.md `--auto` row states the rule.

Tests: test_flow_auto PostMergeCheckout (5381ad036, committed alone). It sets up a bare origin, a squash merge and a deleted remote branch.
- test_returns_to_the_default_branch_keeping_the_sync_write: after the fence, the checkout is on main at origin/main, the tree is clean, and the write is committed on the spec branch.
- test_another_change_keeps_the_checkout_where_it_is: the checkout stays on the branch and the edit survives.
Base vs head: both tests fail by assertion at 5381ad036 (`'# fence:post-merge-checkout' not found`) and pass at b790713bf. Focused gate: test_flow_auto (28), test_flow_merge_destination, test_unattended_skill_fences, test_skill_prose_diet, test_codex_flow_dispatch, test_arg_loop_zsh, test_pilot_backlog_mirror_safety, test_pipeline_qa_auto, test_flow_routing, test_chain_consumer_fixtures, test_sync_codex_check: all OK. baseline: green (conductor handoff, test_flow_auto at f18d99df).

Not run: a live `flow --auto --until=merge` next run on gmickel/flow-next-e2e-scratch. Task 5's end-to-end run covers it on the final code. Note that task 5's run.sh does `git checkout -q main && git pull` without `set -e`. From the old state that checkout was refused, so its runs started on the merged branch unless someone cleaned up by hand.

Follow-ups (outside Touches, not done):
- Root cause: make-pr's tracker finalize (`tracker sync --op reconcile --event makePr`) writes the spec JSON after `make-pr-create.sh` pushed. Neither the PR nor the default branch ever gets that write, including a tracker link created there by create-if-unlinked. Land's terminal touchpoint reads the head spec, which lacks that write.

stage: impl-review - skipped(policy: parallel-wave - conductor reviews after integration)

Conductor fix after review: the fence switched to local main before checking it could fast-forward; a main holding planning commits diverges after the squash merge and the next run started on a stale main. It now switches only when the local default branch is absent or an ancestor of the fetched remote head (2868875f0 + 486f74eaf test, 5a60a2089 fix).
Follow-up found: make-pr writes tracker sync state (including a link it creates for an unlinked spec) into the spec JSON after its push, so it never reaches the PR or main; captured as task 6.

stage: impl-review - ran codex three lenses NEEDS_WORK (1 finding: checkout before fast-forward check) then re-review SHIP (model: gpt-6.1-sol)
stage: plan-sync - skipped(config: planSync.enabled=false)
Tier: session (jev moderate 0.45) at default effort (model: claude-opus-5-5)
## Evidence
- Commits: 755cfc87ab54450993b3692e50be15526284c2c3, daeb9ab76001ce79566d7f330cf5fae818b56ff5, 2868875f0ebd3d8f27fc7b629e5bd1a6d28b9ac6, 486f74eafe842ff57b20f52c45be2cbf2db3ccf6, 5a60a20897964da537021e905b200e9aed18da4d
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_auto.py' (+ flow_routing, codex_flow_dispatch); local bare-repo reproduction of the next-run misroute
- PRs:
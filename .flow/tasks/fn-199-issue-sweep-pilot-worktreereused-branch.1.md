---
satisfies: [R1, R2]
---
# fn-199-issue-sweep-pilot-worktreereused-branch.1 Pilot branch matrix + all-done classification: property-based rules

## Description
Edit plugins/flow-next/skills/flow-next-pilot/workflow.md only (plus regenerated codex mirror).

1. Branch matrix row for plan/plan-review (currently 'git checkout the default branch'): replace with the property-based rule from the spec's API Contracts section - probe current branch for an OPEN PR via gh pr list --head <branch> --state open; no open PR -> stay and dispatch; open PR -> checkout default branch; that checkout fails -> NEEDS_HUMAN naming branch + reason; probe failure -> attempt default-branch checkout, then NEEDS_HUMAN on failure. Update the rationale sentence below the matrix to state the property (never write planning state onto a branch with an open PR), and reconcile the 'If branch checkout fails' row so it does not re-forbid the new stay-put path.

2. All-done classification rule 'MERGED PR exists while the spec is still open: NEEDS_HUMAN': replace per spec - with no OPEN PR, check unshipped work (git rev-list --count <default-base>..<branch-head>, or equivalently merged-PR head == branch head); non-zero -> classify make-pr-eligible and proceed; zero or rev-list failure -> NEEDS_HUMAN as today. Keep alignment with make-pr's Forbidden reused-branch rule.

G1: replace sentences, do not grow the surface with hedging. If test_prompt_text_pinned pins this file, update the hash in the same commit with rationale (deliberate change, issues #354/#355). Run ./scripts/sync-codex.sh twice and commit the mirror diff.

## Acceptance
R1: plan/plan-review dispatch from a secondary worktree whose branch has no open PR (no default-branch checkout required); NEEDS_HUMAN only when the current branch has an open PR AND default-branch checkout fails. R2: merged gate PRs + unshipped commits -> make-pr classification; zero unshipped commits -> NEEDS_HUMAN retained; rev-list failure -> NEEDS_HUMAN. sync-codex.sh idempotent (second run no diff), guards green. Focused tests green.

## Done summary
Replaced pilot's two worktree-hostile rules with the spec's property-based contracts (issues #354/#355): the plan/plan-review branch-matrix row now probes the current branch for an open PR (stay put when none, default-branch checkout only when one exists, NEEDS_HUMAN only when that fallback checkout fails, probe failure degrades fail-safe), and the all-done classification treats merged PR(s) with no open PR + unshipped commits (git rev-list count) as make-pr-eligible, keeping NEEDS_HUMAN for zero unshipped commits or rev-list failure. Rationale sentence, checkout-failure sentence, classification table row, open-PR defer bullet, and crash-class recap all reconciled; codex mirror regenerated. Implementation bridged to cursor-grok-4.6-high; conductor verified the diff against R1/R2 and ran all gates. test_prompt_text_pinned does not pin the pilot workflow, so no hash update was needed.

baseline: green
stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: impl-review - ran (model: claude-fable-5, host backend, round1 NEEDS_WORK round2 SHIP; consider polish committed post-SHIP)
## Evidence
- Commits: 6e239b39b1702b71cc67bf46918224a499b1cfbc, 28097681, 8212ce6f
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_pilot_strikes_prose -q (baseline: green; post-edit: green, 14 tests OK), cd plugins/flow-next/tests && python3 -m unittest test_host_review_backend test_skill_prose_diet test_pilot_strikes test_pilot_strikes_prose test_pilot_backlog_mirror_safety test_pilot_backlog_substrate -q (121 tests OK), ./scripts/sync-codex.sh x2 (idempotent, second run no new diff), cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_pilot_strikes_prose test_skill_prose_diet -q (37 tests OK, post-fix)
- PRs:stage: plan-sync - ran (task .3 docs step updated to shipped head-identity rule; spec prose reconciled; model: claude-fable-5 subagent)

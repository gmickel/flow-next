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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

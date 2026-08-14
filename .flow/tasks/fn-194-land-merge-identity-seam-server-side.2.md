---
satisfies: [R2, R4]
---
# fn-194-land-merge-identity-seam-server-side.2 Server-side catch-up replaces the rebase; §2.6/§2.7 ordering clarified

## Description
R2+R4 in the land skill. R2: §2.8 (~:388-389) - BEHIND plans `catch-up` (renamed from `rebase`); DIRTY routes to the same `catch-up` action (GitHub decides conflicts). §3.3 - REPLACE the entire local rebase block (gh pr checkout / git fetch / git rebase / git push --force-with-lease / branch restore, ~:522-531) with `gh pr update-branch "$PR_NUMBER"` (server-side merge-based catch-up, one API call); non-zero -> verdict BLOCKED, reason base-merge-conflicts-need-hand-resolution; keep the canonical post-push ledger write sourcing the new SHA from `gh pr view --json headRefOid` (no local checkout exists anymore). Rename the action class everywhere: §2.8, §3.3 heading, Phase 4 action enum (~:692), SKILL.md:112 + the safety line :96 ("mechanical rebase only" -> server-side catch-up only), the PLANNED_ACTION list (~:392). Note in the section prose: this removes land's force-push capability and the #302 orphaned-evidence cause; fork PRs fail the same way they failed before (no regression). R4: one paragraph at §2.6/§2.7 stating the evaluation order under reviewSignal: approve - whether the stale-approval detector (~:383) is reachable or shadowed by §2.6's earlier exit, so the agent stops guessing which gate wins (state the truth you find by reading; do not change gate semantics). Static tests: no `git rebase` / `--force-with-lease` remains anywhere in the land workflow; update-branch present with BLOCKED routing; `catch-up` in the action enum; fn-188's §2.9 pins stay green. sync-codex x2. Gate BARE: test_land_config + test_skill_prose_diet.

## Acceptance
R2+R4 met; the rebase machinery is gone; ordering paragraph states the §2.6/§2.7 truth; all pins green; sync-codex idempotent.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

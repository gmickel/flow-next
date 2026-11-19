---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-335-a-pull-agrees-with-a-card-in-the.1 Implement A pull agrees with a card in the configured ready state

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The status decision now knows whether the card is in the configured `tracker.readyState`, using the readiness projection's own per-provider, case-insensitive match (`_desired`). When it is, an unstarted spec (backlog or todo, with a backlog or todo request) agrees with a card that reads as in_progress or in_review: a no-op at the tracker's slot, with no write. Every other pairing decides as before (a policy matrix test checks this).

- Regression (R4): before the fix, a facade pull (`F.sync(op="pull")`, the `tracker sync --op pull` entry point) reproduced `status conflict (unmapped)` for all 4 providers × {no tasks, one todo task}. The issue's backlog/unstarted rows already agree on main (`early-agree`), so they are recorded as already fixed.
- The tracker-sync status reference was updated, the tracker MANIFEST regenerated, the codex mirror synced, and the changelog credits @sn-furali (#627).

stage: impl-review - ran (model: gpt-6.2-sol) round 1 NEEDS_WORK (3 draws, 1 merged finding: review-named ready state normalizes to in_review), fixed; round 2 SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: c3c9d2295606ae11026411af5989180fad1f5e94, bb1ba2af4387f25b7949e55b21a0c4ed1ba5caa5, 8e42e04a2e1d206a09da78b74ec7e8e2ce68ae53
- Tests: python3 -m unittest tests.test_tracker_status tests.test_tracker_facade tests.test_tracker_distribution
- PRs:
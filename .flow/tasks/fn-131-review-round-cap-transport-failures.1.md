---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-131-review-round-cap-transport-failures.1 Implement transport-aware review round accounting

## Description
Make review-round accounting verdict-aware without weakening the pre-dispatch
cap reservation. Codex, Copilot, Cursor, and the prose-driven RP route must
refund reservations that produce no reviewer verdict, record every outcome,
and stop repeated transport failures through a separate bounded error surface.

## Acceptance
- [ ] Shared flowctl accounting records verdict attempts, refunds no-verdict
      transport attempts, and never refunds SHIP/NEEDS_WORK/MAJOR_RETHINK.
- [ ] Consecutive transport failures are bounded independently (default 2);
      exceeding the budget exits distinctly from convergence-cap exit 4.
- [ ] Codex/Copilot/Cursor impl, plan, and completion wrappers use the shared
      finalizer; RP workflows record every response through the CLI.
- [ ] `review-rounds attempts` reports real and refunded counts plus the
      durable attempt trail; cap errors report those counts.
- [ ] Canonical review skills, generated Codex mirror, CLI docs, and changelog
      describe transport refunds and prohibit manual cap resets for flakes.
- [ ] Focused regression suite covers missing verdict, nonzero/timeout/empty
      failures, verdict-bearing outcomes, transport bound, CLI, and wrappers.

## Quick commands

```bash
cd plugins/flow-next/tests
python3 -m unittest test_review_convergence_cap -q
cd ../../..
./scripts/sync-codex.sh
git diff --exit-code -- plugins/flow-next/codex
```

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

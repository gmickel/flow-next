---
satisfies: [R1]
---
# fn-203-rolling-frontier-scheduling-with-shared.2 Author the two rolling prototype branches (prose-only)

## Description
Create the two treatment-arm prototypes as branches of this repo, per the frozen pre-registration. Prose-only edits; never merged to main.

**Size:** M
**Files:** on prototype branches only: plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-work/references/wave-join.md, plus a branch-local lock script for arm 2
**Touches:** [] (no main-branch files; all edits live on eval branches)

### Approach
- Arm 1 branch: rewrite Phase 3 to per-worker-return admission with the five conditions judged against the in-flight set; per-task integration reusing the wave-join SHA/evidence normalization; conductor-owned review via the host-deferred handover shape.
- Arm 2 branch: same admission rule; no integration step; staging-by-declaration prose; edit-state ledger + re-run-before-counting verify rules; a branch-local commit-lock script following the existing cross-process-lock pattern in flowctl (never a shipped flowctl verb - the real verb is Phase B, task 5).
- Reviewer, completion-review, and quality-audit surfaces stay byte-identical to shipped on both branches - diff them to prove it.

### Investigation targets
**Required** (read before editing):
- `plugins/flow-next/skills/flow-next-work/phases.md:95-353` - Phase 3 wave loop (conditions 109-124, report block 138-148, claim 150-164, dispatch 186-262, join 264-300, plan-sync gate 322-353)
- `plugins/flow-next/skills/flow-next-work/references/wave-join.md:16-109` - join report, collision handling, reviewer-overlap point, SHA rewrite before done (76-87)
- `plugins/flow-next/agents/worker.md:25-42,352-394` - PARALLEL_WAVE entry, handover branches, verify block

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:42-99` - cross_process_lock pattern the arm-2 lock script mirrors
## Acceptance
- [ ] Both branches exist, phases.md/wave-join edits only plus the arm-2 lock script
- [ ] Review/completion/audit surfaces byte-identical to shipped on both branches (diff shown)
- [ ] Branch contents match the frozen pre-registration
## Done summary
Two prototype branches authored: A1 rolling frontier + isolated worktrees (04c1e832), A2 rolling frontier + shared checkout with commit mutex, staging-by-declaration, edit-state ledger (b7bb6925). Prose-only deltas on the work skill. Closed retroactively 2026-09-04.
## Evidence
- Commits: c821b999, afdf5e57
- Tests: agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen pre-draw; A0 129.1 min, A1 61.9 min, 52.1% saving, decisive band)
- PRs: https://github.com/gmickel/flow-next/pull/365, https://github.com/gmickel/flow-next/pull/376
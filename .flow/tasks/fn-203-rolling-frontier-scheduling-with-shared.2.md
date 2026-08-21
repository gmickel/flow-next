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
Authored the two fn-203 treatment-arm prototype branches per the frozen pre-registration: `eval/rolling-arm1-isolated` (04c1e832: Phase 3 rewritten to per-worker-return admission with the five fail-closed conditions vs the in-flight set, parallel-handover workers, per-task integration reusing wave-join SHA/evidence normalization, conductor-owned review, full suite at quiesce) and `eval/rolling-arm2-shared` (b7bb6925: same admission, no integration step, wave-join.md repurposed as the shared-checkout discipline - staging-by-declaration, commit mutex via new branch-local references/commit-lock.py following flowctl's cross_process_lock pattern, edit-state ledger + re-run-before-counting verify rules). Both parented at the A0 pin 02212557 (4.4.0); review/completion/audit surfaces proven byte-identical by diff; branch SHAs + authoring notes recorded in agent-evals studies/rolling-frontier-2026-08 (arms/README.md + changelog, commit 6921a2f). Eval branches are never merged to main.

stage: impl-review - skipped(config: REVIEW_MODE=none)
## Evidence
- Commits: 04c1e832adff2f34eb405c1cc46430680d2721ee, b7bb6925552b277683b62bed0d6e31a08dbed724
- Tests: baseline: green - cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_cp1252_robustness -q (23 tests OK, pre-edit), verify: same focused suite green post-work (23 tests OK); flowctl gate classify --base 0e039b0bb83fb54c7396297fa277d1137bea6964 -> TIER_B docs-only on the conductor branch (prototype edits live on eval branches, never main), commit-lock.py smoke: serializes; exit 97 on bounded timeout while held; proceeds after release, byte-identity: git diff 02212557..<each eval branch> -- impl-review/plan-review/spec-completion-review skills + agents + templates + scripts = 0 lines on both branches; all phases.md hunks inside Phase 3
- PRs:
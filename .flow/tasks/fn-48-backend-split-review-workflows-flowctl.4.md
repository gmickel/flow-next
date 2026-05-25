---
satisfies: [R2, R5, R6, R7]
---

## Description

Split `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (currently 1126 lines — the largest skill workflow in the codebase) on the same backend-routing principle as fn-48.3. Most of the bulk is the RP-backend prompt template; Codex- and Copilot-backend users load all 1126 lines today.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`, `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (split), new files `workflow-rp.md` / `workflow-codex.md` / `workflow-copilot.md` / `workflow-common.md`, `scripts/sync-codex.sh` (verify), regenerated mirror.

## Approach

Identical pattern to fn-48.3 (landed in commit `b2f6f0e`) — copy that structure verbatim. The fn-48.3 split produced 4 files: `workflow-common.md` (Phase 0 + philosophy + routing), `workflow-codex.md` (41 LOC), `workflow-copilot.md` (53 LOC), `workflow-rp.md` (489 LOC, includes the Fix Loop). SKILL.md routes via a `Step 1: Detect Backend + Load Workflow` table mapping `$BACKEND` → file. Apply the same shape here. <!-- Updated by plan-sync: fn-48.3 landed concrete structure to copy -->

Differences:
- impl-review's workflow.md is ~75% larger than spec-completion-review's, so the split may produce a `workflow-rp.md` north of 500 lines on its own. That's still a net win (codex/copilot users see ≤100 lines instead of 1126), but if the file is unwieldy, consider further intra-RP-section subdivision (`workflow-rp-prompt.md` + `workflow-rp-driver.md`).
- impl-review has more phase substructure than spec-completion-review (impl-review handles per-task scoped reviews + fix loops + receipt sub-types). Map each phase to the right backend file carefully; cross-backend phases (e.g. receipt format) go into `workflow-common.md`.
- `scripts/sync-codex.sh` RP_WARNING loop already prefers `workflow-rp.md` with fallback to `workflow.md` (landed in fn-48.3) — no further sync-codex.sh change needed for this task, just confirm the regenerated mirror picks up `workflow-rp.md`. <!-- Updated by plan-sync: fn-48.3 added RP_WARNING prefer/fallback -->

**Sequencing**: T3 (fn-48.3) has landed (commit `b2f6f0e`). T4 can proceed directly. Only shared touch point with T5 is `scripts/sync-codex.sh`; if both T4 and T5 need to modify it, serialize that single file (use `flowctl dep add` if a real ordering emerges during work). <!-- Updated by plan-sync: fn-48.3 landed -->

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (full file, 1126 lines).
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`.
- The structure landed by fn-48.3 (commit `b2f6f0e`) — `plugins/flow-next/skills/flow-next-spec-completion-review/{SKILL.md,workflow-common.md,workflow-codex.md,workflow-copilot.md,workflow-rp.md}`. Copy the SKILL.md routing pattern (`Step 1: Detect Backend + Load Workflow` table) verbatim. <!-- Updated by plan-sync: fn-48.3 landed -->
- `scripts/sync-codex.sh` — same file-copy logic concerns. RP_WARNING loop (lines ~365-378) already prefers `workflow-rp.md` with `workflow.md` fallback (landed in fn-48.3); no change required from this task. <!-- Updated by plan-sync: fn-48.3 added prefer/fallback -->
- Memory entries: same set as fn-48.3 — `sync-codexsh-tool-substitution-needs-2026-05-18`, `fn-44-review-cycle-lessons-2026-05-21`.

**Optional**:
- `plugins/flow-next/codex/skills/flow-next-impl-review/workflow.md` — current mirror output.

## Acceptance

- [ ] `flow-next-impl-review/workflow.md` is split per backend; each backend file ≤500 lines (lower if possible). `workflow-common.md` holds cross-backend phases (backend detection, receipt format, etc.).
- [ ] SKILL.md routes correctly based on `$BACKEND`.
- [ ] No phase content lost; the union of split files equals the original workflow.md (modulo whitespace).
- [ ] `./scripts/sync-codex.sh` regenerates the mirror cleanly.
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` green for impl-review on RP, codex, copilot.
- [ ] End-to-end behavior unchanged — same verdicts, same receipt format, same per-task scoped diff, same fix-loop semantics.
- [ ] Routing pattern is structurally identical to fn-48.3 (landed commit `b2f6f0e`): SKILL.md `Step 1: Detect Backend + Load Workflow` table mapping `$BACKEND` → `workflow-{codex,copilot,rp}.md`, plus `workflow-common.md` for Phase 0 / philosophy / routing-table. <!-- Updated by plan-sync: fn-48.3 landed -->

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_

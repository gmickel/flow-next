---
satisfies: [R2, R5, R6, R7]
---

## Description

Split `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (currently 1126 lines — the largest skill workflow in the codebase) on the same backend-routing principle as fn-48.3. Most of the bulk is the RP-backend prompt template; Codex- and Copilot-backend users load all 1126 lines today.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`, `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (split), new files `workflow-rp.md` / `workflow-codex.md` / `workflow-copilot.md` / `workflow-common.md`, `scripts/sync-codex.sh` (verify), regenerated mirror.

## Approach

Identical pattern to fn-48.3 — see that task's approach. Reuse the structure that lands there as the template. Differences:
- impl-review's workflow.md is ~75% larger than spec-completion-review's, so the split may produce a `workflow-rp.md` north of 500 lines on its own. That's still a net win (codex/copilot users see ≤100 lines instead of 1126), but if the file is unwieldy, consider further intra-RP-section subdivision (`workflow-rp-prompt.md` + `workflow-rp-driver.md`).
- impl-review has more phase substructure than spec-completion-review (impl-review handles per-task scoped reviews + fix loops + receipt sub-types). Map each phase to the right backend file carefully; cross-backend phases (e.g. receipt format) go into `workflow-common.md`.

**Sequencing**: T3 (fn-48.3) ideally lands first so this task can copy that pattern. But T3 and T4 can run in parallel — they touch disjoint skill files and disjoint `plugins/flow-next/codex/skills/` directories. Only shared touch point is `scripts/sync-codex.sh`; if both tasks need to modify sync-codex.sh, serialize that single file (use `flowctl dep add` if a real ordering emerges during work).

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (full file, 1126 lines).
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`.
- The structure landed by fn-48.3 (if it's done) — copy the routing pattern verbatim.
- `scripts/sync-codex.sh` — same file-copy logic concerns.
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
- [ ] If fn-48.3 has already landed, the routing pattern here is structurally identical (the goal is consistency across the three review skills).

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_

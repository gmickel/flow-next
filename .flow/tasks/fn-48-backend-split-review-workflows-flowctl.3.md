---
satisfies: [R1, R5, R6, R7]
---

## Description

Split `plugins/flow-next/skills/flow-next-spec-completion-review/workflow.md` (currently 645 lines) into per-backend files so only the active backend's workflow content loads into context per invocation. ~430 of the 645 lines are the RP-backend prompt template, which Codex- and Copilot-backend users currently load for no reason.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow.md` (split), new files `workflow-rp.md` / `workflow-codex.md` / `workflow-copilot.md` / `workflow-common.md`, `scripts/sync-codex.sh` (verify/update file copy logic), regenerated mirror under `plugins/flow-next/codex/skills/flow-next-spec-completion-review/`.

## Approach

- Read current `workflow.md` end-to-end. Identify backend boundaries — the file already has `## Codex Backend Workflow` (line 55+), `## Copilot Backend Workflow` (line 92+), and `## RepoPrompt Backend Workflow` (line 139+) sections. Extract each into its own file. The `## Phase 0: Backend Detection` block (line 13-52) and any pre-Phase-0 content (philosophy, preamble) stays in `workflow-common.md` (or moves into SKILL.md if shorter).
- `SKILL.md` becomes the router: after Phase 0 backend detection, the agent reads the matching `workflow-<backend>.md`. The instruction in SKILL.md must be explicit about which file to read for each backend.
- The `Fix Loop (RP)` section (line 572+) and any other RP-specific tail content go into `workflow-rp.md`.
- Verify `scripts/sync-codex.sh` copies the new files correctly to `plugins/flow-next/codex/skills/flow-next-spec-completion-review/`. If sync uses pattern-based file copy (`cp -r` or `find ... -name "*.md"`), no change needed. If it enumerates files explicitly, update the enumeration.
- **Audit sync-codex.sh per `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30`**: enumerate every new tool reference / file reference introduced by the split, confirm sync-codex.sh's rewrite rules still apply correctly to the smaller files.
- Regenerate the mirror: `./scripts/sync-codex.sh`.
- Smoke: `bash plugins/flow-next/scripts/smoke_test.sh` for the spec-completion-review path on all three backends.

**Anti-pattern to avoid** (per `bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18`): the routing prose in SKILL.md must match the actual pre-mutation state of the files. After the split, re-read SKILL.md and confirm the "read workflow-<backend>.md" instruction is correct for each backend.

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow.md` (full file, 645 lines) — to identify exact split boundaries.
- `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md` — to find the right router-insertion point.
- `scripts/sync-codex.sh` — to verify file-copy logic handles the new files; line 183 / 198-201 rewrite rules <!-- Updated by plan-sync: fn-48.1 shifted lines; was 179 / 202 -->.
- Memory entry `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18` — sync-codex.sh Stage 3 pitfalls (sed misses inside code blocks / tables).
- Memory entry `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` — relative-path drift / codex-mirror smoke / JSON-contract gotchas.

**Optional**:
- `plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow.md` — current mirror output (pre-split) to compare against post-split mirror.

## Acceptance

- [ ] `flow-next-spec-completion-review/workflow.md` is split into per-backend files; each backend file is < 200 lines (target — confirm by line count).
- [ ] SKILL.md routes to the correct per-backend file based on `$BACKEND`. Verified by reading the routing logic — when `$BACKEND="codex"`, agent reads `workflow-codex.md` and does NOT need to read the RP or Copilot variants.
- [ ] No phase content is lost — every phase from the original 645-line file lives in exactly one of the split files (or `workflow-common.md` if cross-backend).
- [ ] `./scripts/sync-codex.sh` regenerates the mirror without errors. `plugins/flow-next/codex/skills/flow-next-spec-completion-review/` contains the split structure.
- [ ] Mirror's `workflow-rp.md` / `workflow-codex.md` / `workflow-copilot.md` have their tool-name rewrites applied (e.g. `AskUserQuestion` → numbered-prompt rewrite in the Codex mirror, per existing convention).
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` is green for spec-completion-review on all configured backends (RP, codex, copilot).
- [ ] End-to-end behavior of `/flow-next:spec-completion-review` is unchanged — same verdicts, same receipt format, same fix-loop semantics on each backend.

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_

---
satisfies: [R3, R5, R6, R7]
---

## Description

Split `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (currently 411 lines) on the same backend-routing principle as fn-48.3 / fn-48.4. resolve-pr's structure is different — backend logic is *interleaved* with cross-cutting phases (Phase 0 parse args, Phase 1 fetch feedback, Phase 5 dispatch, Phase 8 reply+resolve) rather than three top-level backend sections. The split may take the form of small `workflow-<backend>.md` files capturing only the backend-divergent parts (e.g. parallel-dispatch differs Claude/Codex vs serial Copilot/Droid), with the bulk staying in `workflow-common.md`.

Additionally, as the third backend-split this lands, document the established pattern in `agent_docs/adding-skills.md` so future skill authors know when to apply backend-split.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md`, `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (split), new files (smaller set than T3/T4), `scripts/sync-codex.sh` (verify), regenerated mirror, `agent_docs/adding-skills.md` (new section on backend-split pattern).

## Approach

- Read current `workflow.md`. Identify the **backend-divergent slices** specifically — most of resolve-pr is platform-agnostic (parsing comments, triaging, validating, replying). The divergences are:
  - **Phase 5 Dispatch**: parallel (Claude Code, Codex 0.102.0+) vs serial (Copilot, Droid). The platform-detection branch on lines 234-253.
  - **Anything else?** — likely small. Confirm by re-reading.
- For divergences this localized, full per-backend files may be overkill. Two reasonable shapes:
  - **(a) Inline keep**: leave the small backend branches inline; only extract if a divergence block exceeds ~50 lines.
  - **(b) Per-backend file**: extract the dispatch section into `workflow-dispatch-parallel.md` + `workflow-dispatch-serial.md`, source-include from main workflow.md.
  - Implementer picks based on what the file actually looks like. Document the choice in the PR body.
- **Update `agent_docs/adding-skills.md`** (small section): "When to split workflow.md by backend — heuristic: ≥50 lines of backend-divergent content makes a split worthwhile. Smaller divergences (a single `case` block on platform name) stay inline." Cite fn-48.3 and fn-48.4 as canonical examples.
- Regenerate mirror; smoke.

**Note on docs-gap-scout finding**: resolve-pr's workflow.md has a "Copilot / Droid" parenthetical at line 237 (serial-dispatch path). fn-48.2 (R8) confirmed Droid is still actively supported (Path A modified — env-var fallback + `Execute` matcher preserved). **The "Copilot / Droid" parenthetical stays.** <!-- Updated by plan-sync: fn-48.2 confirmed Droid alive — no Droid-mention cleanup needed here or in T6 -->

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (full file, 411 lines).
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md`.
- `agent_docs/adding-skills.md` — to identify the right section for the new backend-split guidance.
- Structures landed by fn-48.3 + fn-48.4 (if done) — for consistency.
- Memory entries: `sync-codexsh-tool-substitution-needs-2026-05-18`, `abort-option-copy-must-reflect-pre-2026-05-18`.

**Optional**:
- `plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md` — current mirror output.

## Acceptance

- [ ] `flow-next-resolve-pr/workflow.md` is restructured so that backend-divergent content does not bloat the load for non-applicable backends. Exact form (per-backend files or inline routing) chosen and documented based on the file's actual divergence profile.
- [ ] `agent_docs/adding-skills.md` has a new section (≤30 lines) on the backend-split pattern with a clear heuristic for when to apply it.
- [ ] Mirror regenerates cleanly; smoke green for resolve-pr on all backends.
- [ ] End-to-end behavior unchanged — parallel dispatch on Claude / Codex; serial on Copilot / Droid (Droid confirmed alive by fn-48.2; mentions preserved). <!-- Updated by plan-sync: fn-48.2 verdict -->
- [ ] Routing prose in SKILL.md and workflow.md(s) matches reality (per `abort-option-copy-must-reflect` memory entry — re-verify after the refactor).

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_

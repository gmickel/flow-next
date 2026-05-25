---
satisfies: [R3, R5, R6, R7]
---

## Description

Split `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (currently 411 lines) on the same backend-routing principle as fn-48.3 (landed commit `b2f6f0e`) / fn-48.4 (landed commit `06f6e6f`). resolve-pr's structure is different — backend logic is *interleaved* with cross-cutting phases (Phase 0 parse args, Phase 1 fetch feedback, Phase 5 dispatch, Phase 8 reply+resolve) rather than three top-level backend sections. The split may take the form of small `workflow-<backend>.md` files capturing only the backend-divergent parts (e.g. parallel-dispatch differs Claude/Codex vs serial Copilot/Droid), with the bulk staying in `workflow-common.md`. <!-- Updated by plan-sync: fn-48.3 + fn-48.4 landed -->

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
- **Update `agent_docs/adding-skills.md`** (small section): "When to split workflow.md by backend — heuristic: ≥50 lines of backend-divergent content makes a split worthwhile. Smaller divergences (a single `case` block on platform name) stay inline." Cite fn-48.3 (commit `b2f6f0e`, landed structure: `workflow-common.md` + `workflow-{codex,copilot,rp}.md` + SKILL.md routing table) and fn-48.4 (commit `06f6e6f`, same 4-file shape; `workflow-common.md` ended up at 565 lines — over the ≤500 target — accepted as trade-off vs duplicating the gated Deep-Pass / Validator / Walkthrough phases into each backend file; auxiliary files `deep-passes.md` / `walkthrough.md` were untouched) as canonical examples. <!-- Updated by plan-sync: fn-48.3 + fn-48.4 landed concrete pattern -->
- Regenerate mirror; smoke.

**Note on docs-gap-scout finding**: resolve-pr's workflow.md has a "Copilot / Droid" parenthetical at line 237 (serial-dispatch path). fn-48.2 (R8) confirmed Droid is still actively supported (Path A modified — env-var fallback + `Execute` matcher preserved). **The "Copilot / Droid" parenthetical stays.** <!-- Updated by plan-sync: fn-48.2 confirmed Droid alive — no Droid-mention cleanup needed here or in T6 -->

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (full file, 411 lines).
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md`.
- `agent_docs/adding-skills.md` — to identify the right section for the new backend-split guidance.
- Structure landed by fn-48.3 (commit `b2f6f0e`): `plugins/flow-next/skills/flow-next-spec-completion-review/{SKILL.md,workflow-common.md,workflow-codex.md,workflow-copilot.md,workflow-rp.md}` — copy SKILL.md routing-table pattern. Structure landed by fn-48.4 (commit `06f6e6f`): `plugins/flow-next/skills/flow-next-impl-review/{SKILL.md,workflow-common.md,workflow-codex.md,workflow-copilot.md,workflow-rp.md}` — same 4-file shape; `workflow-common.md` 565 LOC (over ≤500 target, accepted as trade-off); auxiliary `deep-passes.md` / `walkthrough.md` untouched. <!-- Updated by plan-sync: fn-48.3 + fn-48.4 landed -->
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
Inline-kept resolve-pr's workflow.md (backend divergence is one ~22-line Phase 5 — below the ≥50-line split threshold) and added a 27-line backend-split heuristic section to agent_docs/adding-skills.md citing fn-48.3 (b2f6f0e), fn-48.4 (06f6e6f), and fn-48.5. Fixed stale SKILL.md description (Codex 0.102.0+ is parallel, not serial). Codex mirror regenerates cleanly; resolve-pr smoke 58/58, impl-review 74/74.
## Evidence
- Commits: 4aa65a050f8ab38bd3272834fb7fdeec39b9f056
- Tests: bash plugins/flow-next/scripts/resolve-pr_smoke_test.sh (58/58 PASS), bash plugins/flow-next/scripts/impl-review_smoke_test.sh (74/74 PASS), bash scripts/sync-codex.sh (zero errors)
- PRs:
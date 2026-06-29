---
satisfies: [R9, R10, R12]
---

## Description

Surface `cursor` in the three review skills + setup, then regenerate the Codex mirror. Skill prose MUST match the real flowctl `cursor` surface built in .1/.2 (the top NEEDS_WORK cause per memory — prose-vs-CLI drift).

**Size:** M–L
**Files:** new `workflow-cursor.md` ×2 (impl-review + spec-completion-review), `flow-next-impl-review/workflow-common.md`, `flow-next-plan-review/workflow.md`, 3 `SKILL.md` + 2 `commands/flow-next/*.md` (the `--review` literals), `flow-next-setup` review.backend config, `scripts/sync-codex.sh` regenerated mirror

## Approach

- Mirror `workflow-copilot.md` → new `workflow-cursor.md` in **both** `flow-next-impl-review/` **and** `flow-next-spec-completion-review/` (both have per-backend workflow files).
- `flow-next-plan-review/workflow.md` — add a `cursor` section (single-file, no per-backend split).
- `flow-next-impl-review/workflow-common.md` — add the `cursor` row to the Phase-0 backend dispatch table.
- Add `cursor` to every user-facing `--review=rp|codex|copilot|none` string in the **8 hand-edited files**: impl-review `SKILL.md` + `workflow-common.md`, plan-review `SKILL.md` + `workflow.md`, spec-completion-review `SKILL.md` + `workflow-common.md`, `commands/flow-next/spec-completion-review.md` + `epic-review.md`. (The 6 codex-mirror copies are auto-regenerated — never hand-edit.)
- `flow-next-setup` — `review.backend` prompt/validation accepts `cursor` and the spec form `cursor:gpt-5.5-high`.
- Re-run `scripts/sync-codex.sh`; verify the mirror — R2-block injection position intact (no mid-sentence break), prose matches the real flowctl subcommands, and check the `REVIEW_MODE: none|rp|codex` literal (sync-codex.sh ~:288) for whether cursor needs surfacing.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/` — `workflow-copilot.md` (template), `workflow-common.md`, `SKILL.md`
- `plugins/flow-next/skills/flow-next-spec-completion-review/` — `workflow-copilot.md` (template), `workflow-common.md`, `SKILL.md`
- `plugins/flow-next/skills/flow-next-plan-review/workflow.md`, `SKILL.md`
- `plugins/flow-next/commands/flow-next/spec-completion-review.md`, `epic-review.md`
- `plugins/flow-next/skills/flow-next-setup/` — review.backend config surface
- `scripts/sync-codex.sh` (esp. `:288` `REVIEW_MODE` literal)

## Key context

Codex-mirror discipline (memory): mirror regen exposes latent canonical gaps; treat the first post-regen review as a canonical-gap audit. fn-74 adds **no new skill or command** (workflow-cursor.md is a reference file under an existing skill) — so plugin/marketplace manifest skill/command counts do NOT change, and there is no new flow-next.dev page → navbars untouched.

## Acceptance

- [ ] `/flow-next:impl-review` routes `BACKEND=="cursor"` to `workflow-cursor.md`; `/flow-next:plan-review` + `/flow-next:spec-completion-review` handle `cursor`; new `workflow-cursor.md` present in impl-review + spec-completion-review (R9)
- [ ] every `--review=rp|codex|copilot|none` string in the 8 hand-edited files includes `cursor` (R9)
- [ ] `flow-next-setup` `review.backend` accepts `cursor` and `cursor:gpt-5.5-high` (R10)
- [ ] `scripts/sync-codex.sh` re-run; `cursor` surfaces in `plugins/flow-next/codex/**`; R2-block injection intact; install/sync parity tests pass (R12)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

# fn-80-gate-repoprompt-steering-in-impl-review.1 Apply the fn-78 RP_ELIGIBLE gate to impl-review & spec-completion-review steering + mirror regen

## Description

Copy the shipped fn-78 `RP_ELIGIBLE` guard (see `flow-next-plan-review/SKILL.md` for canonical wording) into `flow-next-impl-review/SKILL.md` and `flow-next-spec-completion-review/SKILL.md`, branching their user-facing backend steering on eligibility. Gate the guidance echoes in both skills' `workflow-common.md` (`:35` ASK-error hint, `:39` override echo). Regenerate the Codex mirror. CHANGELOG Unreleased entry. Steering only — resolution untouched. Do not disturb the adjacent Foreground-rule text added in 2.5.3.

## Acceptance

- **R1:** The `RP_ELIGIBLE` guard (identical predicate to fn-78: `uname == "Darwin"` OR `command -v rp-cli`) is computed in canonical `flow-next-impl-review/SKILL.md` and `flow-next-spec-completion-review/SKILL.md` before their backend-guidance text renders.
- **R2:** When `RP_ELIGIBLE=0`, both skills' steering — Backends summary, "Backend at a glance" (the "**rp** — … Primary backend." line), ASK-error messages, and `--review=…` override-hint echoes (SKILL.md sites + `workflow-common.md:35,39` in each skill) — omits rp and lists only `codex`/`copilot`/`cursor` (+ `none`).
- **R3:** When `RP_ELIGIBLE=1`, all surfaces render byte-for-byte as today.
- **R4:** Resolution untouched: explicit `--review=rp` / `FLOW_REVIEW_BACKEND=rp` / `review.backend=rp` / per-task `review:` override still resolves to rp and reaches `require_rp_cli()`; `--review=rp` stays in the accepted-flag grammar; `workflow-rp.md` files unmodified.
- **R5:** `scripts/sync-codex.sh` run; regenerated `plugins/flow-next/codex/**` committed; `git diff --exit-code plugins/flow-next/codex/` clean after a second regen; no hand-edits to the mirror.
- **R6:** Verification per fn-78 R9a/b: inspect canonical + mirror text for both skills in both eligibility states (rp absent + clean lists when 0; byte-identical when 1).
- **R7:** CHANGELOG `## Unreleased` entry. NO version bump. Docs: extend the fn-78 non-Mac annotation only where these two skills are explicitly named as offering rp (docs/platforms.md general note already exists).

**Files:** `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`, `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md`, `plugins/flow-next/codex/**` (regen), `CHANGELOG.md`.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

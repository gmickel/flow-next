# fn-80-gate-repoprompt-steering-in-impl-review.1 Apply the fn-78 RP_ELIGIBLE gate to impl-review & spec-completion-review steering + mirror regen

## Description

Copy the shipped fn-78 `RP_ELIGIBLE` guard (see `flow-next-plan-review/SKILL.md` for canonical wording) into `flow-next-impl-review/SKILL.md` and `flow-next-spec-completion-review/SKILL.md`, branching their user-facing backend steering on eligibility. Gate the guidance echoes in impl-review's `workflow-common.md` (`:35` ASK-error hint + `:39` override echo) and spec-completion-review's `workflow-common.md` (`:35` ASK-error hint only — its backend echo has no list). Regenerate the Codex mirror. CHANGELOG Unreleased entry. Steering only — resolution untouched. Do not disturb the adjacent Foreground-rule text added in 2.5.3.

## Acceptance

- **R1:** The `RP_ELIGIBLE` guard (identical predicate to fn-78: `uname == "Darwin"` OR `command -v rp-cli`) is computed **locally in every file whose text it gates** — both SKILL.md files AND each skill's `workflow-common.md` Phase 0 (self-contained docs; never reference the guard without computing it in-file). 3-line duplication is intentional (fn-78 inline-over-helper decision).
- **R2:** When `RP_ELIGIBLE=0`, steering omits rp, listing only `codex`/`copilot`/`cursor` (+ `none`). Per-file: **impl-review** SKILL.md (Backends summary, at-a-glance rp/"Primary backend" line, ASK-error, override hints) + `workflow-common.md:35` AND `:39`; **spec-completion-review** SKILL.md (`:35,43,61,65,70,115`) + `workflow-common.md:35` ONLY (its backend echo prints just `Review backend: $BACKEND`, no list — NOT gated).
- **R3:** When `RP_ELIGIBLE=1`, all surfaces render byte-for-byte as today.
- **R4:** Resolution untouched: explicit `--review=rp` / `FLOW_REVIEW_BACKEND=rp` / `review.backend=rp` / per-task `review:` override still resolves to rp and reaches `require_rp_cli()`; `--review=rp` stays in the accepted-flag grammar; `workflow-rp.md` files unmodified.
- **R5:** `scripts/sync-codex.sh` run; regenerated `plugins/flow-next/codex/**` committed; `git diff --exit-code plugins/flow-next/codex/` clean after a second regen; no hand-edits to the mirror.
- **R6:** Verification per fn-78 R9a/b: inspect canonical + mirror text for both skills in both eligibility states (rp absent + clean lists when 0; byte-identical when 1).
- **R7:** CHANGELOG `## Unreleased` entry. NO version bump. Docs: extend the fn-78 non-Mac annotation only where these two skills are explicitly named as offering rp (docs/platforms.md general note already exists).

**Files:** `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`, `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md`, `plugins/flow-next/codex/**` (regen), `CHANGELOG.md`.

## Done summary
Applied the fn-78 RP_ELIGIBLE gate (uname==Darwin OR rp-cli on PATH) to impl-review and spec-completion-review steering: guard computed locally in both SKILL.md files and both workflow-common.md Phase 0 blocks; Backends summaries, glance-list rp/"Primary backend" lines, and ASK-error/override hints now omit rp when ineligible, while --review=rp grammar, resolution, and workflow-rp.md stay untouched. Codex mirror regenerated (idempotent), platforms.md/troubleshooting.md fn-78 notes extended to name the two skills, CHANGELOG Unreleased entry added, no version bump. Cursor impl-review verdict: SHIP (first pass, all R1-R7 covered).
## Evidence
- Commits: a47f49a40c17e4b480602192ba47ee6875ee38b8
- Tests: plugins/flow-next/scripts/ci_test.sh (67/67 pass), plugins/flow-next/scripts/impl-review_smoke_test.sh (74/74 pass), scripts/sync-codex.sh second-regen idempotence (git diff --exit-code plugins/flow-next/codex/ clean), RP_ELIGIBLE gate executed in both states (macOS eligible=1 byte-identical echoes; fake-Linux PATH shim ineligible=0 rp omitted)
- PRs:
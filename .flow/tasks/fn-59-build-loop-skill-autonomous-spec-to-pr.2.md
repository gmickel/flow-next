---
satisfies: [R4, R11]
---

## Description

Teach plan, work, and make-pr the autonomous mode: parse the `mode:autonomous` arg token AND honor `FLOW_AUTONOMOUS=1` env — in their question-suppression branches only, never the ralph-guard/receipt paths.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/SKILL.md` + `steps.md`, `plugins/flow-next/skills/flow-next-work/SKILL.md` + `phases.md`, `plugins/flow-next/skills/flow-next-make-pr/SKILL.md` + `workflow.md` (+ `phases.md` if its Ralph note needs the extra clause)

## Approach

Per spec R4/R11 (amended: token primary, env secondary). NEW parse branch per skill — do NOT overload capture's `mode:autofix`:
- **plan**: SKILL.md option-parsing gains `mode:autonomous` (strip token; suppress the setup questions → defaults grep/short/configured-backend unless passthrough flags present); steps.md Step-1 readiness soft-check's non-interactive branch (:97 region) adds the token/env to its existing `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` probe (memory `env-marker-gate-must-scan-the-namespace`: pattern-match the marker family, don't enumerate rigidly).
- **work**: SKILL.md branch/review questions suppressed under token/env — branch defaults deterministically to `--branch=new` when unset (gap-analysis blocker: Phase 2's "user's answer" never exists under autonomy and Current-on-main would commit to main); Ralph Mode Rules (:50 region) gains the autonomous variant WITHOUT the receipt obligations; phases.md worker env passthrough (:452 region) forwards `FLOW_AUTONOMOUS` when set.
- **make-pr**: TWO SEPARATE FLAGS, never piggyback — `RALPH=1` derives ONLY from `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` (workflow.md:31 + SKILL.md:69, unchanged); a new `AUTONOMOUS=1` derives from `mode:autonomous`/`FLOW_AUTONOMOUS`. Behavior matrix: Phase-0 prompts hard-error when `RALPH || AUTONOMOUS`; `--draft` forced (Layer-1, `--ready` ignored w/ note) when `RALPH || AUTONOMOUS`; the `PR_URL=` stdout contract / receipt / harness semantics remain `RALPH`-only. Autonomy ≠ Ralph.
- All three: the suppression must surface as `NEEDS_HUMAN`-style clean reporting when a genuinely unanswerable ambiguity hits (never hang on a question).

## Investigation targets

**Required:**
- `.flow/specs/fn-59-build-loop-skill-autonomous-spec-to-pr.md` §Resolved at planning
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:31-44` — the token-parse shape to replicate (NOT reuse)
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:1138-1169` — DRAFT_FLAG 4-layer matrix (extend Layer 1)
- `plugins/flow-next/skills/flow-next-plan/steps.md:77-109` — readiness soft-check non-interactive branch
- `plugins/flow-next/skills/flow-next-work/SKILL.md:40-110` — Ralph rules + option parsing

**Optional:**
- `.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04` — gate-shape lesson

## Acceptance

- [ ] All three skills parse + strip `mode:autonomous` and honor `FLOW_AUTONOMOUS=1`; questions suppressed, safe defaults applied (work → `--branch=new`)
- [ ] make-pr: separate `AUTONOMOUS` flag (never sets/piggybacks `RALPH`); prompts hard-error + draft forced on `RALPH || AUTONOMOUS`; `PR_URL=` stdout/receipt semantics stay RALPH-only
- [ ] No ralph-guard hook activation under either signal (grep the hook matchers to prove)
- [ ] Sub-skill mirror prose passes sync-codex validators (regen + commit rides .3); R2-block placements verified for any touched ask-sites
- [ ] Manual smoke: `plan <spec> mode:autonomous --review=none` and `make-pr <spec> mode:autonomous` run question-free on a scratch spec

## Done summary
plan, work, and make-pr now parse+strip the mode:autonomous token and honor FLOW_AUTONOMOUS=1 in their question-suppression branches only: plan defaults short/grep/configured-backend and its readiness soft-check treats the non-interactive marker family; work gains an Autonomous Mode section (deterministic --branch=new default, no receipt obligations) and forwards FLOW_AUTONOMOUS to workers; make-pr carries a separate AUTONOMOUS flag that hard-errors prompts and forces draft under RALPH || AUTONOMOUS while PR_URL= stdout/receipt semantics stay Ralph-only. Codex mirror regen deliberately rides fn-59.3; rp impl-review SHIP first pass.
## Evidence
- Commits: 2b5259b91f9876e1a9c15e419235894453d0490f
- Tests: python3 (all 50 plugins/flow-next/tests/test_*.py) — 0 failures, ./scripts/sync-codex.sh — exit 0, validators pass (mirror diff reverted; regen rides fn-59.3), extracted-bash smoke: make-pr SKILL.md mode-detection block executed with token/env/none variants (AUTONOMOUS parsed+stripped, SPEC_ID intact), extracted-bash smoke: make-pr workflow.md 4.2 draft matrix executed across RALPH/AUTONOMOUS/OPEN_ITEMS/DRAFT_FORCE — all 6 cases per spec incl. --ready ignored under autonomous, grep proof: ralph-guard.py:927 activation keyed solely on FLOW_RALPH==1; zero FLOW_AUTONOMOUS in hooks; PR_URL bash gate stays RALPH-only
- PRs:
## Description

Documentation, sync-codex regeneration, and version bump. Gates on all code tasks completing.

**Size:** M
**Files:**
- `plugins/flow-next/README.md`
- `CLAUDE.md` (project guide)
- `plugins/flow-next/codex/**` (regenerated)
- All three plugin manifests (bumped)
- `CHANGELOG.md`

## Approach

**CLAUDE.md** (project guide):
- Add a short block under the flow-next commands list documenting spec grammar:
  ```
  Review backend spec grammar: backend[:model[:effort]]
    codex:gpt-5.4:xhigh
    copilot:claude-opus-4.5:high
    rp  (bare — RP uses window-level model)
  Valid values: flowctl review-backend --help
  ```
<!-- Added by plan-sync: task 4 delivered these observable behaviors worth documenting alongside the grammar -->
- Note that `flowctl review-backend --json` returns `{backend, spec, model, effort, source}` (spec-form round-trippable); text mode still prints just the bare backend for back-compat.
- Note Ralph surface: `config.env` accepts spec form on `PLAN_REVIEW` / `WORK_REVIEW` / `COMPLETION_REVIEW`; `ralph.sh` exports full spec via `FLOW_REVIEW_BACKEND` and exposes derived `PLAN_REVIEW_BACKEND` / `WORK_REVIEW_BACKEND` / `COMPLETION_REVIEW_BACKEND` (bare backend, via `${VAR%%:*}`) to prompts for branching.

**plugins/flow-next/README.md**:
- Extend `#### Configuration` block to show spec-form examples for `FLOW_REVIEW_BACKEND` and `review.backend` config key.
- Add a small table of backend × supported models × supported efforts. <!-- plan-sync note: pull catalog from flowctl.py:1715 BACKEND_REGISTRY. codex models: gpt-5.4, gpt-5.2, gpt-5, gpt-5-mini, gpt-5-codex. codex efforts: none, minimal, low, medium, high, xhigh. copilot models: claude-sonnet-4.5, claude-haiku-4.5, claude-opus-4.5, claude-sonnet-4, gpt-5.2, gpt-5.2-codex, gpt-5-mini, gpt-4.1. copilot efforts: low, medium, high, xhigh (note: claude-* models drop --effort at runtime). rp/none: no models/efforts. -->
- Note: per-task pinning via `flowctl task set-backend fn-X.Y --review codex:gpt-5.2`.
- Note the precedence cascade (per-task > per-epic > env > config > backend-default).

**CHANGELOG.md**: new `[flow-next X.Y.Z]` entry — "Unified review backend spec parser: `backend:model:effort` form accepted at all surfaces (env, config, per-task, per-epic). Legacy bare-backend values still work."

**Generated codex mirror**:
```bash
scripts/sync-codex.sh
```

**Version bump**:
```bash
scripts/bump.sh minor flow-next
```
<!-- Updated by plan-sync: fn-28 is a feature-level change (new --spec flag on all 6 cmd_*_review, new spec-form support in env/config/per-task/per-epic cascade, new parse_backend_spec_lenient + resolve_review_spec helpers, Ralph spec-form wiring). fn-27 went 0.29.4 → 0.30.0 as a minor; fn-28 should follow suit: 0.30.0 → 0.31.0. Patch is not appropriate. -->

**Tests verified green**: run `plugins/flow-next/scripts/smoke_test.sh` (67 tests — unchanged through fn-28.4) and `python3 -m unittest discover -s plugins/flow-next/tests` (112 tests total as of fn-28.4 — 56 from task 1 + 24 from task 2 + 18 from task 3 + 14 from task 4: TestReviewBackendCmd + TestRalphBareBackendExtraction) before committing the bump. <!-- Updated by plan-sync: counts refreshed from fn-28.4 evidence (98 → 112, +14 from task 4 cmd_review_backend + Ralph bare-backend extraction tests; smoke still 67) -->

## Investigation targets

**Required:**
- `plugins/flow-next/README.md` — Configuration block location
- `CLAUDE.md` — flow-next commands section
- `CHANGELOG.md` — existing entry format
- `scripts/sync-codex.sh` — run it, don't read it (unless it fails)
- `scripts/bump.sh` — confirm patch mode behavior

**Optional:**
- `plans/` runbooks — skim for any spec-grammar references that need updates (unlikely)

## Acceptance

- [ ] CLAUDE.md has a concise spec-grammar block with examples
- [ ] `plugins/flow-next/README.md` shows spec form in Configuration section with precedence cascade documented
- [ ] Backend × models × efforts table exists in README
- [ ] CHANGELOG.md entry added
- [ ] `scripts/sync-codex.sh` has been run; codex mirror reflects all skill changes from task 4 (6 review skill files: impl/plan/epic × SKILL.md+workflow.md, plus flow-next-setup workflow)
- [ ] `scripts/bump.sh minor flow-next` has bumped all three manifest versions consistently (0.30.0 → 0.31.0) <!-- Updated by plan-sync: minor, not patch — fn-28 is feature-level -->
- [ ] `jq . .claude-plugin/marketplace.json` parses cleanly
- [ ] `plugins/flow-next/scripts/smoke_test.sh` green (67 tests — unchanged from fn-28.4)
- [ ] `python3 -m unittest discover -s plugins/flow-next/tests` green (112 tests — 56 from task 1, +24 from task 2, +18 from task 3, +14 from task 4) <!-- Updated by plan-sync: fn-28.4 landed 14 new unit tests (TestReviewBackendCmd + TestRalphBareBackendExtraction) -->

**Receipt schema note for docs** <!-- Added by plan-sync -->:
- Receipts now include a `spec` field alongside `model` + `effort`: `{"mode": "codex", "model": "gpt-5.4", "effort": "high", "spec": "codex:gpt-5.4:high"}`. README should mention this if it documents receipt schema. The `spec` field is the canonical round-trippable form (via `str(resolved_spec)`); `model` + `effort` stay for backward compatibility.
- [ ] No hand edits under `plugins/flow-next/codex/**`

## Done summary
Documented spec-grammar surface across CLAUDE.md + plugin README (Configuration section, backend x models x efforts table, 7-level precedence cascade, review-backend --json shape, receipt schema, inspect commands) and CHANGELOG (flow-next 0.31.0). Regenerated codex mirror (sync-codex), then bumped 0.30.0 -> 0.31.0 across all three manifests + README badges. Final gates green: 112 unittest + 67 smoke.
## Evidence
- Commits: 253bce8e920cff86d581b67aca6097aacdca0591
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (112 pass), cd /tmp && bash plugins/flow-next/scripts/smoke_test.sh (67 pass), bash scripts/sync-codex.sh (16 skills + 20 agents + hooks.json regen; all validations green), bash scripts/bump.sh minor flow-next (0.30.0 -> 0.31.0 across marketplace.json + both plugin manifests), jq . .claude-plugin/marketplace.json plugins/flow-next/.claude-plugin/plugin.json plugins/flow-next/.codex-plugin/plugin.json (all parse; all at 0.31.0), grep -c -- '--spec' codex mirror skill files (24 occurrences across 6 review skill files — matches upstream), manual: FLOW_REVIEW_BACKEND=codex:gpt-5.4:xhigh flowctl review-backend --json returns full {backend, spec, model, effort, source} shape, manual: FLOW_REVIEW_BACKEND=codex flowctl review-backend text mode prints bare 'codex' for skill grep back-compat
- PRs:
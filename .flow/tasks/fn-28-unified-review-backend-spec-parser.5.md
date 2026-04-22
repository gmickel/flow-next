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
scripts/bump.sh patch flow-next
```

**Tests verified green**: run `plugins/flow-next/scripts/smoke_test.sh` (67 tests as of fn-28.3 — unchanged) and `python3 -m unittest discover -s plugins/flow-next/tests` (98 tests total as of fn-28.3 — 56 from task 1 + 24 from task 2 + 18 from task 3) before committing the bump. Task 4 may add more unit/smoke tests; update the counts here when those land. <!-- Updated by plan-sync: counts refreshed from fn-28.3 evidence (was 80 after fn-28.2; +18 from fn-28.3 --spec/resolve_review_spec tests) -->

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
- [ ] `scripts/sync-codex.sh` has been run; codex mirror reflects all skill changes from task 4
- [ ] `scripts/bump.sh patch flow-next` has bumped all three manifest versions consistently
- [ ] `jq . .claude-plugin/marketplace.json` parses cleanly
- [ ] `plugins/flow-next/scripts/smoke_test.sh` green (67+ tests)
- [ ] `python3 -m unittest discover -s plugins/flow-next/tests` green (98+ tests — 56 from task 1, +24 from task 2, +18 from task 3, plus any from task 4) <!-- Updated by plan-sync: fn-28.3 landed 18 new unit tests -->

**Receipt schema note for docs** <!-- Added by plan-sync -->:
- Receipts now include a `spec` field alongside `model` + `effort`: `{"mode": "codex", "model": "gpt-5.4", "effort": "high", "spec": "codex:gpt-5.4:high"}`. README should mention this if it documents receipt schema. The `spec` field is the canonical round-trippable form (via `str(resolved_spec)`); `model` + `effort` stay for backward compatibility.
- [ ] No hand edits under `plugins/flow-next/codex/**`

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)

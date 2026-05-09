---
satisfies: [R12, R18, R36]
---

## Description

Rewrite all Ralph init templates to use `flowctl spec *` verbs and the new `SPECS_FILE` env var (alias `EPICS_FILE` is preserved at the flowctl level per T2 R36). New Ralph installs initialized via `/flow-next:ralph-init` will get spec vocabulary from the start; existing user installs (with `EPICS_FILE=...` in their `config.env`) continue to work via T2's alias.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh` (87 refs)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md` (11 refs)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_plan.md` (6 refs)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_work.md` (2 refs)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env` (2 refs)

## Approach

- `ralph.sh`: wholesale rewrite -- `epics_dir` -> `specs_dir`, `EPICS` -> `SPECS`, `EPICS_FILE` -> `SPECS_FILE`, `epic_id` -> `spec_id`, `flowctl epic close` -> `flowctl spec close`, `flowctl epic set-*-review-status` -> `flowctl spec set-*-review-status`, `--epics-file` -> `--specs-file`, function names like `epic_all_tasks_done`, `list_open_epics`, `maybe_close_epics` -> `spec_all_tasks_done`, `list_open_specs`, `maybe_close_specs`, blocked_by_epic_deps reason code -> `blocked_by_spec_deps`.
- `prompt_completion.md`: `/flow-next:epic-review {{EPIC_ID}}` -> `/flow-next:spec-completion-review {{SPEC_ID}}`, `flowctl checkpoint save --epic {{EPIC_ID}}` -> `--spec {{SPEC_ID}}` (note: T1+T2 alias `--epic` to `--spec` for the checkpoint helper). Template variable `{{EPIC_ID}}` renamed to `{{SPEC_ID}}` consistently across all four prompt templates.
- `prompt_plan.md`: `flowctl epic set-plan-review-status` -> `flowctl spec set-plan-review-status`.
- `prompt_work.md`: minor prose updates.
- `config.env`: comment-only changes (`# Epic completion gate` -> `# Spec completion gate`); the actual env var name in the template file shifts from `EPICS_FILE=` to `SPECS_FILE=` (the alias keeps existing user `config.env` files working).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh` (1230+ lines).
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md`.
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env`.

**Optional:**
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md` -- check for any inline references that mirror the templates.

## Key context

- `SPECS_FILE` and `--specs-file` are the new canonical names; T2 (alias layer) ensures `EPICS_FILE` and `--epics-file` continue to resolve. Existing user installs need NO `config.env` edits.
- `{{EPIC_ID}}` template variable: pure template-substitution rename; when `/flow-next:ralph-init` regenerates a user's scripts, the new templates use `{{SPEC_ID}}`.
- Ralph hooks for skill restrictions reference skill names, NOT epic vocabulary -- no changes there.

## Acceptance

- [ ] `ralph.sh` template has zero `flowctl epic` invocations; uses `flowctl spec *` exclusively.
- [ ] All four prompt templates (`prompt_completion.md`, `prompt_plan.md`, `prompt_work.md`, plus any others under templates/) use `{{SPEC_ID}}` and `flowctl spec *`.
- [ ] `config.env` template uses `SPECS_FILE=` going forward.
- [ ] A fresh `/flow-next:ralph-init` (post-merge) writes templates that use the new vocabulary.
- [ ] An existing user `config.env` with `EPICS_FILE=epics.txt` continues to work (validated in T12 alias smoke test).

## Done summary
Rewrote all Ralph init templates (ralph.sh, four prompt templates, config.env) for spec vocabulary: epic_id → spec_id, EPIC_ID → SPEC_ID, flowctl epic * → flowctl spec *, --epics-file → --specs-file, EPICS_FILE → SPECS_FILE, function names (epic_all_tasks_done → spec_all_tasks_done, list_open_epics → list_open_specs, maybe_close_epics → maybe_close_specs), reason code blocked_by_epic_deps → blocked_by_spec_deps, /flow-next:epic-review → /flow-next:spec-completion-review. Existing user installs continue to work via T2's alias permanence guarantee plus an in-script env-var cascade (SPECS_FILE > EPICS_FILE > SPECS list > EPICS list). get_progress now scans both .flow/specs/ (canonical post-1.0) and legacy .flow/epics/ with canonical winning on conflict.
## Evidence
- Commits: 4fa2b9aaa, c107e67, 3e8709e, 468bfb9
- Tests: bash -n templates/ralph.sh (syntax check), python3 get_progress smoke (fresh / legacy / both-present layouts) -- all expected outputs, bash /tmp/test-cascade.sh (env-var cascade: SPECS_FILE > EPICS_FILE > SPECS list > EPICS list), flowctl codex impl-review --base f008c34 (NEEDS_WORK -> NEEDS_WORK -> SHIP)
- PRs:
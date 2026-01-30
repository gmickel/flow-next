# fn-22-53k.7 docs: update flowctl.md, ralph.md, README.md

## Description

Update documentation to cover epic-completion review feature.

**Files to update:**

1. **`plugins/flow-next/docs/flowctl.md`** — Add new commands:
   - `epic set-completion-review-status <fn-N> --status ship|needs_work|unknown` (after `epic set-plan-review-status`)
   - `codex completion-review` command (implemented in task fn-22-53k.6)
   - `next --require-completion-review` flag documentation

2. **`plugins/flow-next/docs/ralph.md`** — Add completion review gate:
   - New section after "Plan Review Gate" (~line 295): "Epic-Completion Review Gate"
   - Configuration variable: `COMPLETION_REVIEW` (no separate REQUIRE_ flag per epic spec)
   - Update flowchart to show completion_review gate before epic close
   - Receipt path: `completion-fn-N.json`

3. **`plugins/flow-next/README.md`** — Feature overview:
   - Add `/flow-next:epic-review` to commands table (~line 935)
   - Document `completion_review_status` field in .flow/ directory section (~line 1234)
   - Brief mention in Features section

**Naming consistency (must match everywhere):**
- Epic fields: `completion_review_status`, `completion_reviewed_at`
- Env var: `COMPLETION_REVIEW` (no separate REQUIRE_ per epic spec line 68)
- Receipt: `completion-fn-N.json`, type `completion_review`
- Selector: `--require-completion-review`, status `completion_review`

**Pattern reference:** Follow existing plan-review docs structure

## Acceptance

- [ ] flowctl.md documents `epic set-completion-review-status` command
- [ ] flowctl.md documents `codex completion-review` command
- [ ] flowctl.md documents `--require-completion-review` flag on `next`
- [ ] ralph.md has "Epic-Completion Review Gate" section
- [ ] ralph.md configuration reference includes `COMPLETION_REVIEW`
- [ ] README.md commands table includes `/flow-next:epic-review`
- [ ] README.md documents `completion_review_status` epic field

## Done summary
Document epic-completion review feature across flowctl.md, ralph.md, README.md. Added command refs, config vars, receipt schemas, and command reference. Fixed inconsistencies across SKILL.md/workflow.md regarding receipt policy.
## Evidence
- Commits: 7b7fe87, 2053eb2, 3807a70, daf8074
- Tests: grep pattern verification
- PRs:
---
satisfies: [R4, R5]
---
# fn-221-claude-cli-review-backend-claude-p-as-a.3 workflow-claude.md in the three review skills, setup menu, enumeration sweep

## Description
Give the three review skills a `workflow-claude.md`, add `claude` to every backend enumeration in skill prose, extend the setup review-backend menu, and regenerate the codex mirror (R4 and the skill half of R5). Split from the docs task so the skill-prose review runs against the conduct checklists on its own.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-impl-review/{SKILL.md,workflow-claude.md,workflow-common.md,references/backend-specs.md}`, `plugins/flow-next/skills/flow-next-plan-review/{SKILL.md,workflow-claude.md}`, `plugins/flow-next/skills/flow-next-spec-completion-review/{SKILL.md,workflow-claude.md,references/backend-at-a-glance.md}`, `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/**, plugins/flow-next/agents/**, plugins/flow-next/codex/**, scripts/sync-codex.sh]

### Approach
- `workflow-claude.md` in each skill: copy the sibling `workflow-cursor.md` (101 / 40 / 71 lines), swap backend name, argv notes (stdin prompt, `dontAsk`, `--tools Read Grep Glob` as the whole tool set with `--strict-mcp-config`, the diff delivered by path under `.flow/tmp/claude-review/`, `--effort` present), session notes (sessions persist in the CLI's store; re-review, deep pass and validate resume via `--resume <session_id>` from the receipt, the cursor shape), and add one advisory line: on Claude Code hosts the verdict is same-family; prefer `codex` or `host` there when family independence matters.
- Routing tables: impl-review `SKILL.md:11-15`, plan-review `SKILL.md:13-17`, completion-review `SKILL.md:11-15` gain `BACKEND=claude → workflow-claude.md`.
- Enumeration sweep (every line, not a sample): impl-review `SKILL.md` ~23-24, 37-38, 48, 65, 251; plan-review `SKILL.md` ~28, 40, 47, 53; completion-review `SKILL.md` ~23-24, 37-38, 48, 64, 83, 123, 194 (the `codex|copilot|cursor|host) RECEIPT_REQUIRED=true` case); `workflow-common.md:54,79-85` runnable examples; `references/backend-specs.md:15,19`; `references/backend-at-a-glance.md:13,17` with the grammar `claude[:<model>[:<effort>]]`. Executable dispatch arms inside the review skills that the literal-pipe grep does not catch: `flow-next-impl-review/optional-phases.md` (~160 and ~301) switch on the backend in separate case arms for the deep and validator passes; each needs a `claude` arm that resumes via the receipt like the cursor arm. The codex-mirror generator `scripts/sync-codex.sh` (~555) emits the work skill's `REVIEW_MODE` enum from its own hardcoded heredoc (`SECTION3C`), so the canonical `phases.md` edit must ALSO land in that heredoc or the mirror silently regenerates without `claude` at exit 0; verify the generated `codex/` output names `claude`, not just that the sync is idempotent. Operational consumers outside the review skills (these route or parse the backend, not just describe it): `flow-next-work/SKILL.md:113` backend list, `flow-next-work/phases.md:305` `REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred` enum and every branch that switches on it, `flow-next-plan/SKILL.md:144,147` configured-backend sentence and tip, `flow-next-pilot/SKILL.md` "Unattended runs" `--review=` list, and any `agents/*.md` prompt that names the backend set. Finish with `grep -rn 'codex|copilot|cursor' plugins/flow-next/skills plugins/flow-next/agents` (excluding `codex/`) and read every hit.
- Setup `workflow.md`: `HAVE_CLAUDE=$(command -v claude ...)` beside the cursor probe (~289-296), a Claude CLI row in each AskUserQuestion variant (~498-539) with the same-family note, the case mapping (~754-762), the status line (~925), the fallback note (~668).
- Run `./scripts/sync-codex.sh` twice; the mirror must be clean and the guards green. Review the diff against `agent_docs/conduct/impl-review.md`, `plan-review.md`, `spec-completion-review.md`, `setup.md` items.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-impl-review/workflow-cursor.md` — copy source
- `plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md` — how effort is documented
- `plugins/flow-next/skills/flow-next-setup/workflow.md:280-300,490-545,750-765` — menu plumbing
- `scripts/sync-codex.sh` — guards that read skill prose
**Optional:**
- `agent_docs/conduct/README.md` — checklist index
- `.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md`

### Key context
- Canonical prose uses Claude-native tool names; the mirror rewrites them. `claude` as a backend value is not a tool dispatch, so no new transform is expected, but a guard failure is load-bearing: fix the content, never relax the guard.
- Cursor, Droid, Grok and OpenCode read canonical prose as-is: the setup menu row needs no host-specific clause beyond "when the `claude` CLI is on PATH".

### Acceptance
- [ ] Three `workflow-claude.md` files exist and are routed from their `SKILL.md`; each carries the same-family advisory line
- [ ] `grep -rn 'rp|codex|copilot|cursor' plugins/flow-next/skills plugins/flow-next/agents` (excluding the mirror) shows no backend enumeration or parse branch missing `claude`; the work skill's `REVIEW_MODE` enum and the plan skill's configured-backend sentence accept `claude`
- [ ] Setup offers Claude CLI when `claude` is on PATH and maps the choice to `review.backend claude`
- [ ] `./scripts/sync-codex.sh` twice: idempotent, guards green, mirror committed, and `grep -n claude plugins/flow-next/codex/skills/flow-next-work/phases.md` shows the regenerated `REVIEW_MODE` enum carrying `claude`
- [ ] `optional-phases.md` deep and validator arms dispatch `flowctl claude deep-pass` / `flowctl claude validate` with the receipt
- [ ] Skill-shape suites green: `cd plugins/flow-next/tests && python3 -m unittest test_skill_frontmatter test_sync_codex -q` (or the nearest existing suites named in the repo)
## Acceptance
- [ ] TBD

## Done summary
Added `workflow-claude.md` to impl-review, plan-review, and spec-completion-review (stdin prompt, `--tools Read Grep Glob --strict-mcp-config` as the whole tool set, the diff delivered by path under `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff`, `--resume <session_id>` for re-reviews, deep-pass and validate, `"effort": null` at the ladder floor, and the same-family advisory line), routed from each `SKILL.md`. Swept every backend enumeration and parse branch in the review, work, plan, and pilot skills and the worker agent (the `--review=` priority lists, `FLOW_REVIEW_BACKEND` spec-form examples, `RP_ELIGIBLE` backend rosters, the `RECEIPT_REQUIRED` case arm, the `review-backend` return sets, the plan-review accepted explicit modes, `workflow-common.md` runnable examples, `backend-specs.md` / `backend-at-a-glance.md` with the `claude[:<model>[:<effort>]]` grammar, the work `REVIEW_MODE` enum, host-deferred and wave-join references). `optional-phases.md` gained `claude` arms dispatching `flowctl claude deep-pass` / `flowctl claude validate` with the receipt. Setup: `HAVE_CLAUDE` probe, a Claude Code CLI row in all three review menus with the same-family note, the `"Claude"*|"claude"*` answer mapping to `review.backend claude`, the fallback note, the current-config and summary lines. `scripts/sync-codex.sh` SECTION3C heredoc carries the widened enum; the mirror was regenerated twice (idempotent, guards green) and `codex/skills/flow-next-work/phases.md` names `claude` in `REVIEW_MODE`.

Not shipped (follow-up for the conductor): Ralph-harness support for `claude` in `flow-next-ralph-init` (detection menu, `config.env`, `ralph.sh` gates, the three prompt templates) was written, reviewed SHIP, then reverted in 39bd0672 because the prompt templates are SHA-pinned by `test_prompt_text_pinned.py` and the pin lives outside this task's Touches. The spec's R4 binds the Ralph guard only (task .2 shipped it), so the harness support is its own change with its own pin update. Consequence for the AC grep: `flow-next-ralph-init/SKILL.md` and its templates still enumerate rp/codex/copilot/cursor. Also not built: the fan-out secondary-draw allowlist stays codex/copilot/cursor (flowctl enforces it; `workflow-codex.md` is accurate as-is). `require_claude()` still reports only `claude not found in PATH` (task .2 follow-up, a docs pointer decision for .4). Tests pinning the backend set (`test_foreground_rule_fences.INVOKE`, `test_skill_prose_diet.BACKENDS`) do not yet cover the claude workflow fences; extending them is outside Touches.

baseline: green (`cd plugins/flow-next/tests && python3 -m unittest test_skill_prose_diet test_foreground_rule_fences test_backend_spec test_flowctl_surface test_review_fanout_prose_contract test_setup_cursor_host test_skill_prose_flowctl_surface test_review_route test_claude_review_commands -q`, 266 OK; the task's named suites `test_skill_frontmatter` / `test_sync_codex` do not exist, so the nearest suites above were used). After: focused suites 404 OK, `python3 scripts/run_tests_parallel.py` green (204 files, 4775 tests), `uvx ruff@0.16.0 check .` clean; green receipt `.flow/tmp/green-receipts/39bd0672-unittest.json`. `flowctl gate classify` returned FULL (agents/ prefix), so no GATE_SKIPPED lines.

Memory: updated `bug/integration/adding-a-review-backend-sweep-all-2026-06-29` with the three enumeration shapes the pipe-form grep misses (comma/backtick prose lists, slash-form return sets, copied receipt-key prose) and the widened sweep command.

stage: impl-review - ran [codex fan-out round 1 NEEDS_WORK (2 merged findings: plan-review accepted modes omitted claude; floor receipt effort is null not absent) -> fix d593fd7a -> round 2 SHIP -> ralph-init revert 39bd0672 -> re-review SHIP]
## Evidence
- Commits: 29958e4f21daca032eb14860b6bd44f7a553240b, d593fd7a39e7c693a0f9d5cef05aaaff7139ba3a, 39bd067296beab7e427c679d47c56ffc93f62d1e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_skill_prose_diet test_foreground_rule_fences test_backend_spec test_flowctl_surface test_review_fanout_prose_contract test_setup_cursor_host test_setup_grok_host test_skill_prose_flowctl_surface test_review_route test_claude_review_commands test_ralph_guard test_ralph_docs_truth test_work_reached_path_routes -q (404 OK; baseline 266 OK), ./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex (clean, guards green), python3 scripts/run_tests_parallel.py (204 files, 4775 tests, OK; receipt .flow/tmp/green-receipts/39bd0672-unittest.json), uvx ruff@0.16.0 check . (clean)
- PRs:
stage: plan-sync - skipped(config: planSync.enabled != true)

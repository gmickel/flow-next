---
satisfies: [R5]
---
# fn-221-claude-cli-review-backend-claude-p-as-a.4 Repo docs for the claude backend and the Unreleased entry

## Description
Document the backend everywhere the flow-next repo enumerates backends and stage the changelog entry (the docs half of R5). Runs after the skill task: both regenerate the codex mirror and `sync-codex.sh` rebuilds the whole mirror directory, so the two must not run concurrently.

**Size:** M
**Files:** `README.md` (the Adversarial gates row, line ~76, names RepoPrompt / Codex / Copilot / Cursor), `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/platforms.md`, `plugins/flow-next/docs/reach/*.md`, `plugins/flow-next/docs/troubleshooting.md`, `plugins/flow-next/templates/usage.md`, `CHANGELOG.md`, `plugins/flow-next/codex/**` (regenerated)
**Touches:** [README.md, plugins/flow-next/docs/**, plugins/flow-next/templates/usage.md, CHANGELOG.md, plugins/flow-next/codex/**]

### Approach
- `orchestration.md`: registry enum (~144), config examples (~147-149, ~470, ~489), the "three CLI review backends" sentence (~143), the draw-naming list (~241), and one paragraph in "Route the reviews" on when `claude` is the cross-family pick (non-Claude hosts) versus same-family (Claude Code; prefer `codex`/`host` for independence). Confirm the persona-override note (~216-219) names `claude` beside `cursor`.
- `flowctl.md`: TOC (~84), roster (~101), config line (~1035), config table (~1059, full grammar like codex), grammar examples (~1134), ladder section (~1143-1147: ranking top and the signature: exit 0 with `is_error` and the stderr tag), backend lists (~2124, 2171, 2253, 2308, 2336), and a `### claude` subsection beside `### cursor` (~2433): five subcommands, spec form, stdin transport, `dontAsk` plus `--tools Read Grep Glob` and `--strict-mcp-config` (no shell, no write tool, no MCP), the diff delivered by path under `.flow/tmp/claude-review/`, receipt fields, resume via `--resume <session_id>` for deep pass and validate, auth note.
- `platforms.md`: one short section listing reach per host (Claude CLI installed and authenticated) with the same-family caveat on Claude Code; touch the Grok (~268) and Cursor (~302, ~334) backend lists.
- `docs/reach/*.md` (all seven pages): one dated line each, "Models observed (2026-09-05)" style, naming the `claude` review backend and the ids in the ranking.
- Root `README.md:76`: add Claude to the reviewer list in the Adversarial gates row.
- `troubleshooting.md` (~167): add the claude signature clause beside the codex/copilot/cursor ones.
- `templates/usage.md:109-110`: add `claude:<model>:<effort>` to the `review.backend` line and a per-task example; then `./scripts/sync-codex.sh` twice (the mirror's `usage.md` is generated).
- `CHANGELOG.md` `## Unreleased` → `### Added`, one user-outcome-first bullet per `agent_docs/releasing.md`: a Claude-family review verdict from any host, with the ladder, receipt and fix loop, and the same-family caveat on Claude Code.
- Do not edit the flow-next.dev repo; another agent is working there.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:2433-2455` — `### cursor` subsection to mirror
- `plugins/flow-next/docs/orchestration.md:130-180` — Route the reviews
- `agent_docs/releasing.md` — changelog ordering rules
- `agent_docs/writing-docs.md` — page shape and anchors
**Optional:**
- `plugins/flow-next/docs/reach/cursor.md` — table style for reach pages
- `plugins/flow-next/docs/troubleshooting.md:150-180`

### Key context
- The full unit suite pins content in these docs; run `python3 scripts/run_tests_parallel.py` before handoff even though the classifier calls this docs-only.
- Model ids appear only beside a date; every other example uses `<model>`.

### Acceptance
- [ ] `grep -rn 'rp.*codex.*copilot.*cursor' plugins/flow-next/docs README.md plugins/flow-next/templates/usage.md` shows every enumeration naming `claude`
- [ ] `flowctl.md` has a `### claude` subsection and a TOC link that resolves
- [ ] Seven reach pages each carry one dated claude line; `platforms.md` states the same-family caveat on Claude Code
- [ ] `CHANGELOG.md` Unreleased entry present, outcome-first
- [ ] `./scripts/sync-codex.sh` twice clean; `python3 scripts/run_tests_parallel.py` green; `uvx ruff@0.16.0 check .` clean
## Acceptance
- [ ] TBD

## Done summary
Documented the `claude` review backend everywhere the repo enumerates backends and staged the Unreleased changelog entry (the R5 docs half). `docs/flowctl.md` gained a `### claude` subsection beside `### cursor` (five subcommands, spec form `claude[:model[:effort]]` with the CLI's `low|medium|high|xhigh|max`, stdin transport with the fixed read-only argv `claude -p --output-format json --permission-mode dontAsk --tools Read Grep Glob --strict-mcp-config`, the diff delivered by path under `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff` on primary dispatches only, resume-only sessions via `--resume <session_id>`, receipt fields with `"effort": null` at the floor, the exact unavailable signature, fan-out / Ralph-guard / triage notes) plus its TOC link, the command roster, the config table, the grammar examples, the ladder section, and the architecture / cap / fan-out enumerations. `orchestration.md` carries the registry enum, config examples, a "When `claude` is the cross-family pick" paragraph, the resume/injection and single-dispatch lines, a `claude` persona-override channel bullet, the rung-2 comment, and a bridge-recipe note. `platforms.md` gained `## Claude Code CLI review backend` (reach from every host, the install page beside the `claude not found in PATH` error, the same-family caveat) and the Grok / Cursor / RP backend lists; all seven `docs/reach/*.md` pages carry one dated (2026-09-05) claude line with the ranking ids; `troubleshooting.md` names the claude signature beside the codex/copilot/cursor ones; `teams.md`, `skills.md`, `architecture.md`, `ralph.md`, the root `README.md` adversarial-gates row and `templates/usage.md` (config shortcut + per-task example) name the backend; `CHANGELOG.md` Unreleased has an outcome paragraph and an Added bullet. Codex mirror regenerated twice (idempotent).

Review round 1 (codex three-axis fan-out) found one defect on all three axes: the overview passages keyed "cross-family" on the host name while Cursor, Droid and OpenCode can run Claude writers. Fixed in 78ee4279 by conditioning independence on the writer's model family everywhere (same-family reviews stay allowed and receipted). Memory captured: `bug/integration/cross-family-review-claims-key-on-the-2026-09-05`.

Not built (follow-ups): `GLOSSARY.md`'s "Review backend" definition still enumerates rp/codex/copilot/cursor/host/none (outside this task's Touches); `docs/ralph.md` lines 507-509 (`PLAN_REVIEW` etc. accept `rp, codex, none`) describe the Ralph harness, whose claude support was reverted in task .3 and stays a separate change; `docs/release-history.md` "Notable updates" gets its line at the batched release (needs the version number); flow-next.dev untouched by design. Task .2's `require_claude()` message stays `claude not found in PATH`; the install page is named in `platforms.md` and the `flowctl.md` claude subsection instead.

baseline: green (focused Quick commands 284 OK; sync-codex twice clean; full suite via green receipt 39bd0672 at Phase 1). After: `python3 scripts/run_tests_parallel.py` green at both commits (204 files, 4775 tests, 0 failures) and `uvx ruff@0.16.0 check .` clean; `python3 scripts/check_doc_anchors.py` OK; green receipt minted at `.flow/tmp/green-receipts/78ee4279-unittest.json`. `flowctl gate classify` returned FULL (codex mirror prefix); Verify honored the receipt: GATE_SKIPPED:unittest:green-receipt 78ee4279 - baseline reused from prior post-gate pass.

stage: impl-review - ran [codex fan-out round 1 NEEDS_WORK (1 merged finding, 3 draws) -> fix 78ee4279 -> round 2 SHIP]
## Evidence
- Commits: 8f940687313d133690eac08e974cbe1a28c85db0, 78ee42793a3e13bc53b25e5f8a6d6bdbd5310b65
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_claude_review_commands test_cursor_review_commands test_backend_spec test_model_resolution test_flowctl_surface test_review_prompt_constraints -q, ./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex, python3 scripts/check_doc_anchors.py, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., GATE_SKIPPED:unittest:green-receipt 78ee4279 - baseline reused from prior post-gate pass
- PRs:
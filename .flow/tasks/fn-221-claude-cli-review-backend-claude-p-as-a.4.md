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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

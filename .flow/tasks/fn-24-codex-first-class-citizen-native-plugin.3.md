Run `scripts/sync-codex.sh` (created in task 2) to generate the initial `plugins/flow-next/codex/` directory and commit it.

## Steps

1. Run `scripts/sync-codex.sh` and verify clean output
2. Verify generated structure:
   - `plugins/flow-next/codex/skills/` — 16 skill directories
   - `plugins/flow-next/codex/agents/` — 20 .toml files
   - `plugins/flow-next/codex/hooks.json` — valid JSON
3. Spot-check key patches:
   - `codex/skills/flow-next-work/phases.md` — section 3c uses "worker agent" not "Task tool"
   - `codex/skills/flow-next-plan/steps.md` — scouts use `context_scout` not `flow-next:context-scout`
   - `codex/skills/flow-next-prime/workflow.md` — uses "Use the X_scout agent" not "Task flow-next:X-scout"
   - `codex/agents/agents-md-scout.toml` — renamed from claude-md-scout, references AGENTS.md
   - `codex/agents/worker.toml` — sandbox_mode = "workspace-write", no model (inherited)
   - `codex/agents/build-scout.toml` — model = "gpt-5.4-mini", sandbox_mode = "read-only"
   - `codex/agents/quality-auditor.toml` — model = "gpt-5.4", reasoning = "high", sandbox_mode = "read-only"
4. Verify no bare `${CLAUDE_PLUGIN_ROOT}` refs without fallback: `grep -r 'CLAUDE_PLUGIN_ROOT}/' codex/skills/ | grep -v '.codex\|HOME'`
5. Verify no `Task flow-next:` refs: `grep -r 'Task flow-next:' codex/skills/`
6. Validate all TOML files parse: `for f in codex/agents/*.toml; do python3 -c "import tomllib; tomllib.load(open('$f','rb'))"; done`

## Notes
- This task is just generation + verification + commit. No new code written.
- If any issues found, fix in sync-codex.sh (task 2) and re-run.

## Acceptance criteria
- [ ] `plugins/flow-next/codex/` directory exists with all expected files
- [ ] All spot-checks pass
- [ ] No validation errors
- [ ] Changes committed

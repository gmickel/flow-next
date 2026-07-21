<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v1 -->
## Flow-Next

This project uses Flow-Next for ALL task tracking. `flowctl` is on PATH via the plugin. Do NOT create markdown TODOs or use TodoWrite. Re-anchor (re-read spec + task status) before every task.

- Lifecycle: `flowctl list` / `show fn-N.M` / `start fn-N.M` / `done fn-N.M --summary-file s.md --evidence-json e.json` (e.json: `{"commits": ["<sha>"], "tests": ["<cmd>"], "prs": []}`)
- BEFORE any other flowctl operation, or when unsure of a flag: run `flowctl usage` (CLI cheatsheet + orchestration recipes).
- BEFORE delegating to another model/CLI (`codex exec`, `cursor-agent`, `claude -p`, `grok`) or picking a delegate/review model: run `flowctl usage` and follow "Orchestration & model steering" exactly.
- Creating a spec: `flowctl spec create --title "Short title" --json`, then `flowctl spec set-plan <id> --file plan.md`, then `/flow-next:plan <id>`.
- If `flowctl` is not found: run `/flow-next:setup`.
<!-- END FLOW-NEXT -->

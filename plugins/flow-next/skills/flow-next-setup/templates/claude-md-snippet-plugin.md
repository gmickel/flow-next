<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v1 -->
## Flow-Next

This project uses Flow-Next for ALL task tracking. `flowctl` is on PATH via the plugin. Do NOT create markdown TODOs or use TodoWrite. Cold session: `flowctl brief` first — one bounded call (specs, ready tasks, memory); go deeper with `show`/`cat`/`anchor <task-id>`.

- Lifecycle: `flowctl list` / `show fn-N.M` / `start fn-N.M` / `done fn-N.M --summary-file s.md --evidence-json e.json` (e.json: `{"commits": ["<sha>"], "tests": ["<cmd>"], "prs": []}`)
- BEFORE any other flowctl operation, or when unsure of a flag: run `flowctl usage` (CLI cheatsheet + orchestration recipes).
- BEFORE bridging work to another model/CLI (`codex exec`, `cursor-agent`, `claude -p`, `grok`) or picking an implementation/review model: run `flowctl usage` and follow "Orchestration & model steering" exactly.
- Creating a spec: `flowctl spec create --title "Short title" --plan-file plan.md --json`, then `/flow-next:plan <id>`.
- If `flowctl` is not found: run `/flow-next:setup`.
<!-- END FLOW-NEXT -->

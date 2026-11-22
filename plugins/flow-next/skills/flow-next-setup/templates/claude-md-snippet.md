<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v3 -->

## Flow-Next

This project uses Flow-Next for ALL task tracking. `flowctl` is the flow-next plugin install's `scripts/flowctl` — every flow-next skill resolves it itself; outside a skill, run it by path (last line). Do NOT create markdown TODOs or use TodoWrite. Cold session: `flowctl brief` first — one bounded call (specs, ready tasks, memory); go deeper with `show`/`cat`/`anchor <task-id>`.

- Lifecycle: `flowctl brief` / `show fn-N.M` / `start fn-N.M` / `done fn-N.M --summary-file s.md --evidence-json e.json` (e.json: `{"commits": ["<sha>"], "tests": ["<cmd>"], "prs": []}`)
- BEFORE any other flowctl operation, or when unsure of a flag: run `flowctl usage` (CLI cheatsheet) or `flowctl --help`.
- BEFORE bridging work to another model/CLI (`codex exec`, `cursor-agent`, `claude -p`, `grok`) or picking an implementation/review model: run `flowctl usage --orchestration` and follow "Orchestration & model steering" exactly.
- Creating a spec: write it directly with `flowctl spec create --title "Short title" --plan-file plan.md --json`. Scaffold cascade (first match wins): `SPEC.md` -> `spec.md` -> bundled template.
- Building, implementing or delivering a spec, whether a person or another agent asks: invoke `flow-next:flow-next-flow <spec-id>`; it picks the route. `flow-next:flow-next-plan` (task breakdown) runs only when a person asks for a plan or a task breakdown, or when flow routes there.
- Substantial replies (reports, reviews, multi-section answers): invoke `flow-next:flow-next-prose` BEFORE drafting — the artifact prose contract applies to chat replies too. Short conversational turns skip it.
- Running `flowctl` by hand: it is not on PATH. Resolve it the way the skills do - the plugin install's `scripts/flowctl` (Claude/Droid: plugin-root env var; Codex: `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`; Cursor/Grok: two levels above any flow-next SKILL.md) - or update/reinstall the flow-next plugin. A repo with no `.flow/` yet: run `flow-next:flow-next-setup`.
<!-- END FLOW-NEXT -->

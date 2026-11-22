## Goal & Context

Two token savers salvaged from the discarded efficiency wave 2, as one small change with no gate or compatibility risk.

1. `flowctl usage` is read before most flowctl work but carries about 14 KB of multi-CLI bridge and model-steering recipes that only bridging or model-routing work needs. Split them into their own guide.
2. `/flow-next:deps` runs one `flowctl show` per open spec to collect dependencies. `flowctl specs --json` can carry them, making the gather one call.

## Edge Cases & Constraints

- Projects that never re-run setup keep the old block line: run `flowctl usage` and follow "Orchestration & model steering". Plain `flowctl usage` must still resolve that heading and name the new command.
- A missing template keeps today's error text and exit 1, on both flowctl.py and the bootstrap fast path.
- Installers and smokes that stage `templates/` must ship the new file; the Codex mirror rewrites command syntax in both usage files.
- `specs --json` change is additive; no existing field changes.

## Acceptance Criteria

- **R1:** `plugins/flow-next/templates/usage.md` holds only the CLI cheatsheet and lifecycle workflow; the bridge and model-steering recipes move unchanged to `templates/usage-orchestration.md`, printed by `flowctl usage --orchestration` (flowctl.py and the bootstrap fast path; `usage --help` documents the flag).
- **R2:** Plain `flowctl usage` keeps a `## Orchestration & model steering` heading whose body tells the agent to run `flowctl usage --orchestration`; a test pins the heading and the command.
- **R3:** Pointers to the recipes (setup snippets, Cursor rule, work skill bridge references, setup summary, Codex sync, repo instruction files, `docs/flowctl.md` and other runtime docs) name `flowctl usage --orchestration`.
- **R4:** `flowctl specs --json` includes `depends_on_epics` per spec, with a test.
- **R5:** `flow-next-deps` gathers its graph from one `flowctl specs --json` call; its conduct checklist matches.

## Boundaries

Out of scope: everything else in the fn-346 spec (auto-finalize, land probe, forge readiness, pilot snapshot, compact JSON, preflight, anchor/review-prompt flags, review transport). No version bump, release, or downstream docs.

## Decision Context

The deps skill's old loop also collected `plan_review_status`; nothing later in the skill read it, so it is dropped rather than added to `specs --json`.

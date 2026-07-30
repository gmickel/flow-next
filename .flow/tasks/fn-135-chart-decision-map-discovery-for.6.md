---
satisfies: [R2, R17, R27, R30, R31, R33, R47]
---
# fn-135-chart-decision-map-discovery-for.6 Ship guide router and adjacent skill handovers

## Description
### Objective

Ship the missing `/flow-next:guide` router and wire chart into every adjacent skill boundary. The router is prompt-first and recommends the smallest sufficient workflow; it is not a mandatory front door or another stateful stage.

### Exact files

- `plugins/flow-next/skills/flow-next-guide/SKILL.md` — new stateless routing skill implementing the approved fn-67 scope plus the chart-aware matrix.
- `plugins/flow-next/commands/guide.md` — thin command shim.
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` and `workflow.md` — selected candidate routes to chart only when still singular, oversized, and unclear.
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — clear ideas/briefings route to capture; do not manufacture chart.
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` — existing-spec clarification stays primary; route backward only when the effort itself is not specifiable.
- `plugins/flow-next/skills/flow-next-plan/SKILL.md` and `steps.md` — ready spec stays in plan; unshaped oversized idea routes to chart.
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md` and/or `workflow.md` — chart stays outside the build loop; optional unattended driving stops terminally at attended decisions.
- Existing plugin registries that enumerate public skills/commands.
- `plugins/flow-next/tests/test_guide_routing.py` — new exact matrix, skip/narrow, prompt-first, and boundary contract suite.
- `plugins/flow-next/tests/fixtures/chart_prompt_scenarios/*.json` — extend the shared behavioral scenarios with ambiguous and unambiguous guide traces.
- `plugins/flow-next/tests/test_command_shim_flatten.py` — include guide in the exact shim set.

### Routing matrix to encode

- Domain search -> prospect; selected candidate -> chart only if still unclear/oversized.
- Clear meaningful idea -> capture or direct spec authoring; skip chart.
- Existing structured brief -> capture; narrow/skip interview only after read-back proves no material gaps.
- Valid but ambiguous spec -> interview; do not reopen chart unless the effort itself is not specifiable.
- Ready spec -> plan.
- Tiny local low-risk change -> direct change/review path.
- Planned tasks -> work, then existing review/QA/ship choices.

Guide must explain “skip because the signal is absent” versus “skip despite unresolved risk.” It asks one blocking question only when two routes would materially differ; otherwise it gives one recommendation, why, what may be skipped/narrowed, and a natural-language next prompt.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_guide_routing test_chart_prompt_scenarios test_chart_skill_contract test_command_shim_flatten -q
```

### Non-goals

- No guide state, artifact, or deterministic flowctl command.
- No fixed prospect -> chart -> capture conveyor.
## Acceptance
- `/flow-next:guide` ships as a stateless prompt-first router and covers direct change, prospect, chart, capture/direct spec, interview, plan, work, review/QA/ship.
- Each route names its positive signal and explicit safe skip/narrow condition; chart is recommended only for one oversized/unclear idea.
- Prospect, capture, interview, plan, and pilot handovers agree with the same matrix and preserve their existing ownership boundaries.
- Guide output leads with a natural-language next prompt, not flags; one blocking question is used only for materially different routes.
- Behavioral scenario fixtures prove ambiguous read-back and unambiguous routing into skip-chart, chart, capture, interview, and plan; registries/shims and focused tests pass.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

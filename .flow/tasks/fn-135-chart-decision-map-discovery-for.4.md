---
satisfies: [R1, R2, R3, R4, R5, R7, R8, R9, R15, R17, R20, R26, R27, R28, R29, R33, R35, R36, R37, R43, R46, R47, R48]
---
# fn-135-chart-decision-map-discovery-for.4 Ship prompt-first chart skill and adaptive loop

## Description
### Objective

Ship the canonical prompt-first `/flow-next:chart` skill and command shim. The host agent owns interpretation, chart shaping, frontier judgment, evidence-route dispatch, attended consent, re-charting, briefing proposal, and one terminal verdict.

### Exact files

- `plugins/flow-next/skills/flow-next-chart/SKILL.md` — new canonical entrypoint and routing contract.
- `plugins/flow-next/skills/flow-next-chart/workflow.md` — chart mode, work/status modes, breadth-first frontier, re-chart loop, attended/unattended behavior, briefing handoff.
- `plugins/flow-next/skills/flow-next-chart/references/examples.md` — native prompt/operation examples and four adaptive traces; examples are illustrative, not a mandatory sequence.
- `plugins/flow-next/commands/chart.md` — thin selector shim following current command conventions.
- `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json` — update only where the existing registries enumerate public skills/commands.
- `plugins/flow-next/tests/test_chart_skill_contract.py` — new prose/guard/verdict/context-loading contract suite.
- `plugins/flow-next/tests/test_chart_prompt_scenarios.py` and `plugins/flow-next/tests/fixtures/chart_prompt_scenarios/*.json` — structured host-trace/eval scenarios with expected operations, read-backs, mutations, and verdicts, following the existing `test_prime_eval.py` fixture style.
- `plugins/flow-next/tests/test_command_shim_flatten.py` — add the chart shim to the exact inventory.

### Investigation targets

- Follow the canonical Claude-native / generated-Codex split. Use bare `AskUserQuestion` and `Task` with `subagent_type: Explore`; include portable-host fallbacks required by project guidance. Task 7 runs sync and verifies the generated mirror.
- Chart mode: name/read back Outcome, decide whether real fog exists, sketch only the first breadth-first frontier, report attended/unattended cost before persistence, and resolve nothing.
- Chart mode renders the initial-map proposal and cost before persistence. If it exceeds the ceiling, offer narrowing/splitting first; pass `--force-size --reason` only after an explicit warning/read-back confirms the override.
- Work mode: re-anchor Outcome; call `flowctl chart frontier`; choose one smallest uncertainty; claim; run the evidence route; resolve/scope/release; infer only newly-visible decisions; recompute. Never follow a frozen initial route.
- One work invocation owns exactly one D-ID/claim/verdict. Independent unattended routes fan out only as separate invocations; there is no batch or mixed-result verdict. One attended decision per session. Unattended driver reaching any stored `attendance: attended` decision must persist no answer and emit `NEEDS_HUMAN`.
- Full decision bodies/assets are read on selection, not during ordinary status/frontier navigation.

### Native examples to include

- “This is too broad to capture; help me find the first decision worth making.”
- “We know the storage choice. Record it as background and show what uncertainty disappears; do not invent a resolved decision.”
- “Use the cheapest real-world check for viability.”
- “The prototype changed direction. Preserve the old assumption and redraw.”
- “Show whether this should become one spec or two; do not build yet.”
- “Keep this as one chart despite the size warning” -> read back the count, ceiling, and consequence, then record the consent reason through guarded create.

Each example must show the inferred operation, read-back point, evidence/consent boundary, and terminal `CHART_VERDICT`.

The scenario harness covers known background facts, ambiguous steering that requires read-back, reversal/supersession, attended gating, newly visible frontier growth, crash/stale-claim recovery, skip-chart, and exact terminal verdicts. Static prose tests remain useful but are not evidence for prompt interpretation.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_skill_contract test_chart_prompt_scenarios test_command_shim_flatten -q
```

### Non-goals

- No implementation work hidden inside chart, except a `task` decision that only enables another decision.
- No automatic chart creation when the idea is already capture-ready.
## Acceptance
- Chart mode names/read-backs Outcome, stops without persistence when no fog exists, otherwise creates only the visible frontier and cost estimate while resolving nothing.
- Work mode uses `flowctl chart frontier` as its sole selection input, claims before work, re-charts after every transition, and splits oversized decisions before dispatch.
- Attended prototype/interview decisions cannot self-resolve; unattended driving emits exactly one `CHART_VERDICT=NEEDS_HUMAN` line with no answer write.
- Independent unattended evidence routes fan out only as separate one-D-ID invocations; each has one claim/verdict, and crash recovery is observable through the stored claim.
- Natural-language examples cover known facts, cheapest evidence, reversal/supersession, skip-chart, and one-vs-two-spec briefing without teaching a fixed route order.
- Structured scenario/eval fixtures prove prompt interpretation, read-back, guarded operations, adaptive frontier changes, guide handoff, stale recovery, and exact verdicts; canonical skill/shim/registries and focused commands pass.
- Over-ceiling prompt scenarios prove refusal by default, narrowing/split recommendation, explicit read-back, and audited `--force-size --reason` only after consent.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R1, R2, R3, R4, R5, R7, R8, R9, R15, R17, R20, R26, R27, R28, R29, R33, R35, R36, R37, R43, R46, R47, R48, R49, R51, R52, R53, R55]
---
# fn-135-chart-decision-map-discovery-for.4 Ship prompt-first chart skill and adaptive loop

## Description
### Objective

Ship the canonical prompt-first `/flow-next:chart` skill and command shim. The host agent owns bounded grounding, interpretation, chart shaping, frontier judgment, evidence-route dispatch, prototype presentation and attended consent, tracker-locator re-entry, re-charting, briefing proposal, and one terminal verdict.

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
- Chart mode: build a bounded `## Grounding Snapshot` using the ordered pattern at `plugins/flow-next/skills/flow-next-prospect/workflow.md:355-379`. Read the prompt/attachments, repo strategy/instructions/current implementation, directly relevant specs/chart history, and explicitly connected sources; do not perform open-ended research. Preserve safe evidence references/revisions, surface conflicting/stale/unavailable evidence as uncertainty, and never turn imported background into a D-ID or acceptance-criterion tag.
- Name/read back Outcome, grounding, smallest visible breadth-first frontier, parked fog, and attended/unattended cost before persistence. Ask only questions not already answered by approved evidence; resolve nothing. No consequential fog means stop and recommend the smaller route.
- Chart mode renders the initial-map proposal and cost before persistence. If it exceeds the ceiling, offer narrowing/splitting first; pass `--force-size --reason` only after an explicit warning/read-back confirms the override.
- Work mode: re-anchor Outcome; call `flowctl chart frontier`; choose one smallest uncertainty; claim; run the evidence route; resolve/scope/release; infer only newly-visible decisions; recompute. Never follow a frozen initial route.
- One work invocation owns exactly one D-ID/claim/verdict. Independent unattended routes fan out only as separate invocations; there is no batch or mixed-result verdict. One attended decision per session. Unattended driver reaching any stored `attendance: attended` decision must persist no answer and emit `NEEDS_HUMAN`.
- Prototype work creates or imports one scoped throwaway artefact, records it through `chart attach-asset` while the D-ID remains open, presents the exact safe reference/revision, and records the human reaction before resolve/supersede/graduation. If the reaction does not happen, release normally with an awaiting-reaction note or leave crash state observable; a later invocation resumes from the existing artefact rather than rebuilding or inferring approval.
- Before interpreting a selector as a new idea, call `flowctl chart locate`. A stored parent tracker URL re-enters chart status/frontier; an open decision URL selects that D-ID. Read back canonical ID/title/local record link. Resolved/superseded URLs show history and replacement/frontier options; never silently choose another D-ID. Lookup failures create or mutate nothing and offer the local chart-id path.
- Full decision bodies/assets are read on selection, not during ordinary status/frontier navigation.
- Known facts and resolved decisions retain citations, D-ID links, and approved evidence references. The skill never applies acceptance-criterion trailing tags to chart facts/decisions and never invents a verified/inferred fact grammar ahead of a landed, human-approved fn-148 outcome.

### Native examples to include

- “This is too broad to capture; help me find the first decision worth making.”
- “Here is the outcome and what we already know. Ground this in the repo, show the smallest initial frontier, and do not turn background facts into decisions.”
- “We know the storage choice. Record it as cited background and show what uncertainty disappears; do not invent a resolved decision or source tag.”
- “Use the cheapest real-world check for viability.”
- “The prototype changed direction. Preserve the old assumption and redraw.”
- “Continue this chart from this decision link: `<stored tracker URL>`.” -> resolve locally, read back canonical D-ID/title, and re-anchor before work.
- “Show whether this should become one spec or two; do not build yet.”
- “Keep this as one chart despite the size warning” -> read back the count, ceiling, and consequence, then record the consent reason through guarded create.

Each example must show the inferred operation, read-back point, evidence/consent boundary, and terminal `CHART_VERDICT`.

The scenario harness covers bounded grounding, no-evidence and conflicting/stale evidence, known background facts with evidence references but no acceptance-criterion tags, ambiguous steering that requires read-back, prototype attach/present/react and interrupted resumption, reversal/supersession, attended gating, newly visible frontier growth, tracker parent/decision URL re-entry and failure, crash/stale-claim recovery, skip-chart, and exact terminal verdicts. Static prose tests remain useful but are not evidence for prompt interpretation.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_skill_contract test_chart_prompt_scenarios test_command_shim_flatten -q
```

### Non-goals

- No implementation work hidden inside chart, except a `task` decision that only enables another decision.
- No automatic chart creation when the idea is already capture-ready.
- No chart-level `[user]`/`[paraphrase]`/`[inferred]`/`[strategy:*]` fact grammar and no pre-judgment of fn-148.
## Acceptance
- Chart mode names/read-backs Outcome, stops without persistence when no fog exists, otherwise creates only the visible frontier and cost estimate while resolving nothing.
- Chart kickoff emits a bounded ordered Grounding Snapshot with safe references/revisions, asks no question already answered by approved evidence, and turns conflicts/staleness/missing sources into explicit uncertainty rather than facts or fabricated D-IDs.
- Work mode uses `flowctl chart frontier` as its sole selection input, claims before work, re-charts after every transition, and splits oversized decisions before dispatch.
- Attended prototype/interview decisions cannot self-resolve; unattended driving emits exactly one `CHART_VERDICT=NEEDS_HUMAN` line with no answer write.
- Prototype scenarios prove create/import -> idempotent attach while open -> present exact artefact -> human reaction -> resolve/supersede -> re-chart. Missing reaction preserves the linked artefact and open D-ID for resumption; missing/unsafe artefact prevents resolution.
- Independent unattended evidence routes fan out only as separate one-D-ID invocations; each has one claim/verdict, and crash recovery is observable through the stored claim.
- Natural-language examples cover known facts, cheapest evidence, reversal/supersession, skip-chart, and one-vs-two-spec briefing without teaching a fixed route order.
- Known-fact scenarios preserve citations/D-ID evidence without borrowing acceptance-criterion tags; fn-148 outcome handling is consume-only after a confirmed, human-approved change lands.
- Structured scenario/eval fixtures prove prompt interpretation, read-back, guarded operations, adaptive frontier changes, guide handoff, stale recovery, and exact verdicts; canonical skill/shim/registries and focused commands pass.
- Over-ceiling prompt scenarios prove refusal by default, narrowing/split recommendation, explicit read-back, and audited `--force-size --reason` only after consent.
- Parent and decision tracker URL scenarios resolve through the local ledger, read back canonical identity, and never use remote search/title inference. Unknown/ambiguous/stale/unsafe URLs fail without mutation; historical decisions remain history unless the human selects new frontier work.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

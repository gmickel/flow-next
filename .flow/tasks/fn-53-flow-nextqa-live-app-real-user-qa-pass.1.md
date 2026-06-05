---
satisfies: [R1, R2, R3, R10]
---

## Description
Stand up the `/flow-next:qa` skill skeleton and the **scenario-derivation** core, and prove the whole thesis end-to-end. This is the **early proof point**: given a real spec + a running app, derive ≥1 scenario from the spec, drive it via fn-51 flow-next-drive, and capture one piece of evidence. Validate before investing in the rest.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-qa/SKILL.md`, `plugins/flow-next/skills/flow-next-qa/workflow.md`, `plugins/flow-next/commands/flow-next/qa.md`

## Approach
- Mirror the **make-pr** skill layout: `SKILL.md` (frontmatter `name`/`description`/`user-invocable: false`/`allowed-tools`, FLOWCTL preamble, phase router) + `workflow.md` (discover → derive → prepare → execute → file → verdict). Keep each file ≤500 lines.
- FLOWCTL preamble verbatim: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"` (+ `.flow/bin/flowctl` fallback for subagents).
- **Derive scenarios from the spec** (R2): pull AC/R-IDs via `flowctl spec export-cognitive-aid <spec-id> --json`; AC → scenarios, R-IDs → coverage spine (reuse the make-pr R-ID coverage-table pattern), **Boundaries → what NOT to test** (suppress false bugs), Decision Context → the *Expected* column.
- **Consume fn-51 via a read-and-drive contract, never re-implement driving** (R3): a skill is NOT a callable API — the host agent **reads fn-51's workflow + references and executes the universal flow itself** (`observe → snapshot fresh refs → act → verify → capture`), recording an evidence tuple per scenario `{driver_rung, target_url, viewport, screenshot_path, console_path}`. Point at fn-51's references for driver specifics — never duplicate CDP/agent-browser prose.
- **Lay the `workflow.md` phase skeleton with disjoint, clearly-delimited section anchors** (discover / derive / prepare / execute / file / verdict) so the serial downstream tasks each edit ONE section — 53.3 owns *prepare*, 53.4 owns *execute/autonomy* — keeping the shared file merge-safe.
- Canonical Claude-native tool names (`Task` + `subagent_type: Explore`, `AskUserQuestion`) — `sync-codex.sh` rewrites later (R10; the regen itself is task .5).
- Command stub `qa.md` mirrors `commands/flow-next/work.md` (thin "MUST invoke the skill").

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-make-pr/SKILL.md` — skill skeleton + FLOWCTL preamble template
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:355-382` — R-ID coverage-table render pattern (reuse for R2)
- `plugins/flow-next/skills/flow-next-drive/SKILL.md:32-83` — universal driving flow + ladder + the `:83` hand-off of QA to this skill
- `agent_docs/adding-skills.md:1-24` — the 9-step new-skill registration checklist
- `plugins/flow-next/commands/flow-next/work.md` — command-stub shape

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` (`spec export-cognitive-aid`) — the AC/R-ID payload shape

## Key context
- fn-51 already DEFERS the QA workflow to this skill (`drive/SKILL.md:83`) — the seam is designed; QA orchestrates, fn-51 actuates.
- agent-browser is the only assumed-present driver; everything else is probe-and-degrade. The proof point needs a real running target (e.g. flow-next.dev or any localhost app) — if none is reachable, the proof degrades to "fn-51 routes" without true evidence; flag that explicitly.

## Acceptance
- [ ] `flow-next-qa` skill skeleton exists (SKILL.md + workflow.md) with the discover→derive→prepare→execute→file→verdict phase map; all files ≤500 lines
- [ ] Scenario derivation reads the spec via `spec export-cognitive-aid`: AC→scenarios, R-IDs→coverage, Boundaries→exclusions, Decision Context→expected
- [ ] End-to-end proof: from a real spec, derive ≥1 scenario and dispatch it through the fn-51 read-and-drive contract, recording the evidence tuple; capture a screenshot + console to `.flow/tmp/` when a live target exists, ELSE emit a BLOCKED proof receipt documenting the missing target/driver (R13 path) — the proof still validates derivation + fn-51 handoff + evidence-tuple plumbing
- [ ] `workflow.md` phase skeleton lays disjoint section anchors (prepare / execute) for the serial downstream tasks
- [ ] Canonical Claude-native tool names only (no inline cross-platform tables); `qa.md` command stub created
- [ ] **Forbidden: marking PASS from source inspection** is stated as a hard rule in the skill (R1)

## Done summary
Stood up the /flow-next:qa skill skeleton (SKILL.md + workflow.md + qa.md command stub) with six disjoint, merge-safe phase anchors (discover/derive/prepare/execute/file/verdict + autonomy) for the serial downstream tasks, plus the working discover and derive phases — spec id resolution (branch_name scan + info prompt), base-ref cascade, and the four spec-as-intent mappings (AC->scenarios, R-IDs->coverage spine, boundaries->exclusions, decision-context->expected). Proved the thesis end-to-end: derived a 13-row coverage spine from a real spec and drove flow-next.dev via the fn-51 read-and-drive contract (agent-browser rung), capturing a real screenshot + console and recording the evidence tuple. Hard rule "PASS forbidden from source inspection" stated in the skill.
## Evidence
- Commits: 8e663f2, 86d4241, 64ef6cb
- Tests: bash -n on discover-phase blocks (branch-match + base-detection cascade), spec export-cognitive-aid --section spec round-trip (AC=13/boundaries=6/decision_context=3), end-to-end proof: derive scenarios from real spec + drive flow-next.dev (HTTP 200) via fn-51 agent-browser rung, captured S1-homepage.png + console to .flow/tmp/, recorded evidence tuple in proof-receipt.json, wc -l all three files <=500
- PRs:
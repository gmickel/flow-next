---
satisfies: [R1, R2, R3]
---
# fn-189-human-first-visual-digest-skill.1 Core skill: flow-next-visual SKILL.md + command shim

## Description
Create `plugins/flow-next/skills/flow-next-visual/SKILL.md` (plus `workflow.md` only if SKILL.md alone would exceed ~150 lines - prefer one file). Embed the FULL shape vocabulary from the spec's 'Shape vocabulary' section verbatim in intent (all 8 shapes, one concrete example each, smallest-view selection rule, visual-next-to-its-text rule, one-or-a-few-never-all rule, whole-block rule, trimming rule, mermaid-last-resort). Implement the five digest modes from the spec's 'Digest modes' section with the spec post-plan mode's 6 ordered elements. Grounding guardrails inline: every path/edge/coverage claim from real state (`$FLOWCTL show <id> --json`, task files, `git diff --stat`), never invented; fewer nodes, more honest. Standard `## Preamble` with the `$FLOWCTL` fallback chain (`${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl`, then `.flow/bin/flowctl`). Frontmatter: `name: flow-next-visual`, trigger-rich `description` enabling natural-language invocation (phrases: 'show me', 'explain this visually', 'restate that', 'digest the plan', 'too much text', 'walk me through the spec/tasks/diff'; names the four targets: spec, task, diff, current topic - positive trigger phrases only, no negative/exclusion statements), `allowed-tools` (read-only set + Bash; no Edit/Write/Task). Command shim `plugins/flow-next/commands/visual.md`: bare colon-free `name: visual`, non-empty description, mirroring the audit.md/prospect.md shape. Read-only contract stated in the skill body: chat output only - compact markdown visuals, not images or HTML files; never writes, never mutates flow state. Graceful degradation prose: missing tasks -> pre-plan digest; no spec -> diff/ad-hoc; no flowctl -> ad-hoc with one-line notice.

## Acceptance
R1: skill + shim exist with the exact frontmatter contract; NL trigger phrases present in description. R2: all 8 shapes with examples + all 5 discipline rules present. R3: all five digest modes specified with grounding guardrails; degradation paths stated. Skill references NO Claude-builtin dispatch/ask tools; output pure markdown.

## Done summary
Added the `flow-next-visual` skill (single SKILL.md: 8-shape markdown vocabulary with one example each, the five discipline rules, five digest modes with the spec post-plan 6 ordered elements, grounding guardrails, degradation paths, read-only chat-only contract) plus the flat `commands/visual.md` shim with a bare colon-free `name: visual`.

Scope notes: `EXPECTED_COMMANDS` in test_command_shim_flatten.py gained "visual" because this task's shim breaks that pin directly. The remaining count/listing surfaces (manifest "25 commands, 29 skills" strings, docs/skills.md and docs/README.md counts, README table, guide row, sync-codex mirror, CHANGELOG) are fn-189-human-first-visual-digest-skill.4 (R6/R7) and are the sole full-suite failure below; sync-codex.sh was deliberately NOT run here since REQUIRED_OPENAI_YAML_SKILLS lands in .4 and would fail validation now.

baseline: green (test_command_shim_flatten pre-edit, rc=0)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)
## Evidence
- Commits: cf3ada964b56de47d0bf790d291c28883c73fef5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_command_shim_flatten test_cursor_plugin_surface test_flowctl_surface -q (30 tests, OK), uvx ruff@0.16.0 check . (All checks passed), python3 scripts/run_tests_parallel.py (4489 ran, 1 failure: test_chart_docs_inventory count pins - skill/command counts, owned by fn-189-human-first-visual-digest-skill.4 R7)
- PRs:
stage: plan-sync - ran (no drift; downstream .2-.5 already aligned)

---
satisfies: [R1, R2, R3]
---
# fn-189-human-first-visual-digest-skill.1 Core skill: flow-next-human SKILL.md + command shim

## Description
Create `plugins/flow-next/skills/flow-next-human/SKILL.md` (plus `workflow.md` only if SKILL.md alone would exceed ~150 lines - prefer one file). Embed the FULL shape vocabulary from the spec's 'Shape vocabulary' section verbatim in intent (all 8 shapes, one concrete example each, smallest-view selection rule, visual-next-to-its-text rule, one-or-a-few-never-all rule, whole-block rule, mermaid-last-resort). Implement the five digest modes from the spec's 'Digest modes' section with the spec post-plan mode's 6 ordered elements. Grounding guardrails inline: every path/edge/coverage claim from real state (`$FLOWCTL show <id> --json`, task files, `git diff --stat`), never invented; fewer nodes, more honest. Standard `## Preamble` with the `$FLOWCTL` fallback chain (`${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl`, then `.flow/bin/flowctl`). Frontmatter: `name: flow-next-human`, trigger-rich `description` enabling natural-language invocation (phrases: 'show me', 'explain this visually', 'restate that', 'digest the plan', 'too much text', 'walk me through the spec/tasks/diff'; names the four targets: spec, task, diff, current topic), `allowed-tools` (read-only set + Bash; no Edit/Write/Task). Command shim `plugins/flow-next/commands/human.md`: bare colon-free `name: human`, non-empty description, mirroring the audit.md/prospect.md shape. Read-only contract stated: chat output only, never writes, never mutates flow state. Graceful degradation prose: missing tasks -> pre-plan digest; no spec -> diff/ad-hoc; no flowctl -> ad-hoc with one-line notice.

## Acceptance
R1: skill + shim exist with the exact frontmatter contract; NL trigger phrases present in description. R2: all 8 shapes with examples + all 5 discipline rules present. R3: all five digest modes specified with grounding guardrails; degradation paths stated. Skill references NO Claude-builtin dispatch/ask tools; output pure markdown.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

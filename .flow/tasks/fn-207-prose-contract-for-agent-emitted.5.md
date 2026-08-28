---
satisfies: [R7]
---
# fn-207-prose-contract-for-agent-emitted.5 Stable reply-prose skill /flow-next:prose

## Description
Ship the stable reply-prose skill (R7): trigger-scoped ambient application of docs/prose.md to substantial replies, per the full stable checklist in agent_docs/adding-skills.md (steps 7/8/10 included; user promoted mid-task from the originally planned experimental tier).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-prose/SKILL.md` (new), `plugins/flow-next/commands/prose.md` (new), `scripts/sync-codex.sh`, `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, `plugins/flow-next/skills/flow-next-guide/SKILL.md`, `plugins/flow-next/docs/prose.md`, `CHANGELOG.md`, count-pin tests, `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/flow-next-prose/**, plugins/flow-next/commands/prose.md, scripts/sync-codex.sh, .claude-plugin/marketplace.json, plugins/flow-next/.claude-plugin/plugin.json, plugins/flow-next/.codex-plugin/plugin.json, plugins/flow-next/skills/flow-next-guide/SKILL.md, plugins/flow-next/docs/prose.md, CHANGELOG.md, plugins/flow-next/tests/**, plugins/flow-next/codex/**]

### Approach
- SKILL.md (~25 lines, no bash, no FLOWCTL preamble): frontmatter `name: Flow Prose` + description that (a) triggers on substantial replies/reports/review walkthroughs/summaries and the phrases "/flow-next:prose", "apply the prose contract", "tighten this reply"; (b) excludes short conversational turns, tool-call narration, the visual digest, and any output that lands in a file/PR/tracker (those carry their own pointers); (c) ends with ``. Body: read `../../docs/prose.md` (resolve relative to this SKILL.md; absent -> proceed without it, never block); apply rules 1-10 at draft time, not as an afterpass; dormant for replies: the precedence section's marker/projection bullets, and rule 8 softens to lead-with-the-answer; rule 10 (honesty) fully active; never rewrite quoted material, code, command output, or the user's words.
- Command shim `commands/prose.md`: bare `name: prose`, non-empty description — mirror `audit.md` shape (adding-skills.md step 2).
- sync-codex.sh: `generate_openai_yaml "flow-next-prose" "Flow Prose" "<short desc>" "#F59E0B" false` next to the work-rolling precedent (~L1676) + add to `REQUIRED_OPENAI_YAML_SKILLS`. Run TWICE, commit mirror.
- Registry counts: 27->28 commands, 31->32 skills in the three manifests; update the count-pin test expectations the same way commit 5b9e039f did for chart (registry/filesystem assertions to 32/28/27; published phrases and needles to 31/26 — the carve-out excludes exactly the experimental work-rolling beta and must equal the skills.md table row count).
- Guide: one plain guide matrix row (never a pipeline stage; name it when the user asks for reply prose discipline).
- prose.md line 3: adjust the exclusion sentence — replies are governed opportunistically via the skill (description-triggered, opportunistic); the visual digest stays excluded.
- CHANGELOG: extend the existing Unreleased entry with one sentence, em-dash-free.
- OpenCode: nothing manual (roster-generated command stub); verify once with `./scripts/install-opencode.sh --dest /tmp/oc-proof2 --force` and confirm `commands/flow-next-prose.md` generates and the skill scatters.

### Investigation targets
**Required** (read before coding):
- `agent_docs/adding-skills.md` — steps 1-6, 11-13 + the experimental-tier section (the contract this task executes)
- `plugins/flow-next/skills/flow-next-work-rolling/SKILL.md` frontmatter — the experimental-description precedent
- `plugins/flow-next/commands/audit.md` — command-shim shape
- `scripts/sync-codex.sh:1670-1690` — openai.yaml generation site + REQUIRED array
- `plugins/flow-next/skills/flow-next-guide/SKILL.md:55-65` — work-rolling experimental note shape

**Optional:**
- `plugins/flow-next/tests/test_chart_docs_inventory.py` — ChartRegistryCounts carve-out (count-pin update pattern)

### Key context
- Experimental tier: conduct checklist + README/docs count updates REQUIRED (stable tier); mickel.tech stays maintainer-downstream.
- The skill body is itself artifact-adjacent prose: dogfood it against prose.md's rules (no em dashes, no colon splices).
- Full gate before handoff: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.
- A bot-comment fix agent may push to the branch concurrently — `git pull --rebase` before committing if the remote moved.

### Acceptance
- [ ] `skills/flow-next-prose/SKILL.md` + `commands/prose.md` ship with the exclusion list, and pointer-not-payload body
- [ ] sync-codex openai.yaml entry + REQUIRED row added; `./scripts/sync-codex.sh` twice: idempotent, guards green, mirror committed
- [ ] Registry counts bumped in all three manifests; count-pin tests updated on BOTH registry and published sides
- [ ] Guide matrix row added; prose.md scope sentence adjusted; CHANGELOG Unreleased entry extended (em-dash-free)
- [ ] OpenCode scratch install generates the command stub and scatters the skill
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Acceptance
- [ ] `skills/flow-next-prose/SKILL.md` + `commands/prose.md` ship with the exclusion list, and pointer-not-payload body
- [ ] sync-codex openai.yaml entry + REQUIRED row added; `./scripts/sync-codex.sh` twice: idempotent, guards green, mirror committed
- [ ] Registry counts bumped in all three manifests; count-pin tests updated on BOTH registry and published sides
- [ ] Guide matrix row added; prose.md scope sentence adjusted; CHANGELOG Unreleased entry extended (em-dash-free)
- [ ] OpenCode scratch install generates the command stub and scatters the skill
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

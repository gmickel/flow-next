---
satisfies: [R26]
---

## Description

Cross-platform sync: register `flow-next-make-pr` in `scripts/sync-codex.sh` (`generate_openai_yaml` call + `REQUIRED_OPENAI_YAML_SKILLS` array entry). Run `./scripts/sync-codex.sh` to regenerate `plugins/flow-next/codex/`. Verify the Codex mirror has the rewritten skill (with `request_user_input` instead of `AskUserQuestion`, etc.).

**Size:** S (one new line in sync-codex.sh + one in REQUIRED array; regeneration is automatic)
**Files:** `scripts/sync-codex.sh`, `plugins/flow-next/codex/` (regenerated — many files but all auto-generated)

## Approach

- **`generate_openai_yaml` call** — add at `sync-codex.sh:536` (after `flow-next-memory-migrate`, before the review-red section starts). Workflow blue (`#3B82F6`) is correct color — make-pr is a workflow skill, not review (red) or utility (amber):
  ```bash
  generate_openai_yaml "flow-next-make-pr" "Flow Make PR" "Render a cognitive-aid PR body from flow-next state and open via gh" "#3B82F6" false
  ```
  - 6 args: name, display name, description (≤70 chars), color hex, `allow_implicit_invocation` (always `false` for skills users invoke explicitly), optional default prompt (skip — epic-id is optional positional)
- **`REQUIRED_OPENAI_YAML_SKILLS` array** — add `"flow-next-make-pr"` entry. Place between `"flow-next-memory-migrate"` (line 560 currently) and `"flow-next-impl-review"` (line 561) to keep workflow skills grouped.
- **Run regenerate:**
  ```bash
  ./scripts/sync-codex.sh
  ```
  - Output: `Sync complete: N skills, 21 agents, hooks.json` — N should increment by 1 (was 22 → now 23)
  - Validations to confirm pass:
    - `All N required skills have openai.yaml`
    - `No bare CLAUDE_PLUGIN_ROOT refs`
    - `No 'Task flow-next:' refs`
    - `No Claude-native tool refs in Codex skill prose`
    - `No R17 forbidden vocabulary in Codex mirror`
    - `No R19 strategy-doc fluff in Codex mirror`
- **Inspect Codex mirror** at `plugins/flow-next/codex/skills/flow-next-make-pr/` — verify:
  - Tool names rewritten: `AskUserQuestion` → `request_user_input`, `Task` → `spawn_agent`
  - `agents/openai.yaml` exists with the right metadata (name, display name, color, description)
  - Slash command at `plugins/flow-next/codex/prompts/flow-next:make-pr.md` mirrors the canonical
  - Path patches applied (the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` → `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}` / FLOWCTL local fallback)

## Investigation targets

**Required:**
- `scripts/sync-codex.sh:510-545` — `generate_openai_yaml` function definition + the 9 existing workflow-blue calls
- `scripts/sync-codex.sh:551-567` — `REQUIRED_OPENAI_YAML_SKILLS` array
- `scripts/sync-codex.sh:822-836` — validation block that enforces REQUIRED skills have openai.yaml
- `plugins/flow-next/codex/skills/flow-next-audit/` — example post-sync output structure (compare to canonical to understand sync rewrites)

**Optional:**
- `plugins/flow-next/codex/agents/openai.yaml` — example metadata file format

## Acceptance

- [ ] `scripts/sync-codex.sh` has `generate_openai_yaml "flow-next-make-pr" ...` call inserted at the correct line in the workflow-blue section (between `flow-next-memory-migrate` and the review-red section).
- [ ] `REQUIRED_OPENAI_YAML_SKILLS` array includes `"flow-next-make-pr"`.
- [ ] `./scripts/sync-codex.sh` runs cleanly with all validations passing. Skill count increments by 1.
- [ ] `plugins/flow-next/codex/skills/flow-next-make-pr/SKILL.md` exists with tool-name rewrites applied (`request_user_input` not `AskUserQuestion`).
- [ ] `plugins/flow-next/codex/skills/flow-next-make-pr/agents/openai.yaml` exists with the right metadata.
- [ ] `plugins/flow-next/codex/prompts/flow-next:make-pr.md` exists.
- [ ] No regressions in existing Codex mirror — diff vs pre-sync state shows only additions for make-pr (no removed/modified other skills).

## Done summary
Registered `flow-next-make-pr` in `scripts/sync-codex.sh` (workflow-blue generate_openai_yaml call + REQUIRED_OPENAI_YAML_SKILLS entry) and regenerated `plugins/flow-next/codex/`. Skill count 22 → 23, all validations pass, Codex mirror has tool-name rewrites and FLOWCTL path patches applied; no other skills touched.
## Evidence
- Commits: b37523771efc701277b39506d9d4d2e7292d3712
- Tests: ./scripts/sync-codex.sh
- PRs:
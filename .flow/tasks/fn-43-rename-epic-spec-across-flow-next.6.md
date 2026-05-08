---
satisfies: [R12, R14, R21]
---

## Description

Rename the completion-review slash command, skill directory, and all dispatchers. Move skill content under the new name. Move the command markdown. Leave a thin redirect at the old command path that surfaces a one-line "renamed" notice plus a pointer to the new skill -- the redirect file is prose-only (no code), since the slash-command file body is the prompt. Explicitly delete `skills/flow-next-epic-review/` after move (Claude Code rule: skill name shadows command on collision).

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-epic-review/` -> `plugins/flow-next/skills/flow-next-spec-completion-review/` (full dir move via `git mv`)
- `plugins/flow-next/commands/flow-next/epic-review.md` (moved + thin redirect)
- `plugins/flow-next/commands/flow-next/spec-completion-review.md` (new canonical)
- `scripts/sync-codex.sh` (lines 348, 541, 565)
- `plugins/flow-next/skills/flow-next-work/` (any `/flow-next:epic-review` dispatch references)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md`

## Approach

- `git mv plugins/flow-next/skills/flow-next-epic-review plugins/flow-next/skills/flow-next-spec-completion-review`. Rewrite SKILL.md frontmatter `name:`, all internal prose mentions of "epic" -> "spec", "epic-review" -> "spec-completion-review".
- Move `commands/flow-next/epic-review.md` -> `commands/flow-next/spec-completion-review.md` (canonical content). Rewrite frontmatter + body so the command points at the new skill.
- Create a NEW thin file `commands/flow-next/epic-review.md` containing the one-line redirect notice. Body shape: H1 + 3-5 lines of prose explaining the rename and pointing at the new skill. NOT a copy of the canonical file. Slash-command body is the prompt; the agent reads "renamed; use spec-completion-review" and dispatches.
- IMPORTANT: explicitly verify `skills/flow-next-epic-review/` is fully gone after move. A leftover `SKILL.md` would shadow the redirect command per Claude Code precedence rules.
- `scripts/sync-codex.sh`:
  - Line 348: `for skill in flow-next-impl-review flow-next-plan-review flow-next-epic-review` -> drop or rename `flow-next-spec-completion-review`.
  - Line 541: `generate_openai_yaml "flow-next-epic-review"` registration -> `"flow-next-spec-completion-review"`.
  - Line 565: `REQUIRED_OPENAI_YAML_SKILLS` array -> rename entry.
- Update dispatchers:
  - `flow-next-work/phases.md` and any other skill that mentions `/flow-next:epic-review` by name: rewrite to `/flow-next:spec-completion-review`.
  - Ralph init template `prompt_completion.md`: rewrite invocation.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-epic-review/SKILL.md` + `workflow.md` + `flowctl-reference.md`.
- `plugins/flow-next/commands/flow-next/epic-review.md`.
- `scripts/sync-codex.sh:348, 541, 565`.
- `plugins/flow-next/skills/flow-next-work/phases.md` (dispatcher).
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md`.

**Optional:**
- All other skills repo-wide for stragglers (`grep -r "/flow-next:epic-review" plugins/flow-next/`).

## Key context

- The redirect command file is **prose only**, not code. Claude Code injects the markdown body as the prompt. The redirect tells the agent: "this command is renamed; use the new skill". The agent does the dispatch.
- Skill directory name shadows command name on collision. Leaving any file under `skills/flow-next-epic-review/` will block the redirect command from working as expected.

## Acceptance

- [ ] `skills/flow-next-spec-completion-review/` exists with renamed contents; `skills/flow-next-epic-review/` directory does not exist.
- [ ] `commands/flow-next/spec-completion-review.md` is the canonical command file.
- [ ] `commands/flow-next/epic-review.md` exists as a thin redirect (3-5 lines of prose pointing at the new skill).
- [ ] `sync-codex.sh` has zero references to `flow-next-epic-review` (renamed); all references use `flow-next-spec-completion-review`.
- [ ] After T13 runs `sync-codex.sh`, Codex mirror at `plugins/flow-next/codex/skills/flow-next-spec-completion-review/` exists and has `agents/openai.yaml` registered.
- [ ] All in-repo dispatchers (`flow-next-work/phases.md`, ralph-init `prompt_completion.md`) reference the new name.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:

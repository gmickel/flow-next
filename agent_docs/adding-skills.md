# Adding a new user-facing skill (checklist)

When adding a new `/flow-next:<name>` skill, every step below MUST be done. Skipping any creates silent Codex degradation that won't surface for releases.

1. **Canonical skill** at `plugins/flow-next/skills/flow-next-<name>/SKILL.md` (+ `workflow.md` / `phases.md` as needed). Frontmatter: `name`, `description`, `user-invocable: false` (default for slash-only skills), `allowed-tools`.

2. **Slash command** at `plugins/flow-next/commands/flow-next/<name>.md` (mirror existing `audit.md` / `prospect.md` shape).

3. **Tool names in canonical = Claude-native** — write `AskUserQuestion`, `Task`, etc. directly. NO inline cross-platform tables. If you reference these tools, optionally add a parenthetical "(`sync-codex.sh` rewrites to `request_user_input` for Codex)" for maintainer clarity — sync strips it from the Codex mirror.

4. **`scripts/sync-codex.sh` `generate_openai_yaml` call** added in the appropriate section (workflow blue `#3B82F6`, review red `#EF4444`, utility amber `#F59E0B`). Include display name, short description, brand color, explicit `false` for `allow_implicit_invocation`, optional default prompt.

5. **`scripts/sync-codex.sh` `REQUIRED_OPENAI_YAML_SKILLS` array** updated to include the new skill name. Validation will fail otherwise.

6. **Run `./scripts/sync-codex.sh`** — verify zero errors, all REQUIRED skills have `agents/openai.yaml`, and the Codex mirror has the rewritten tool names. Commit the regenerated `plugins/flow-next/codex/` directory.

7. **Commands list** updated in:
   - `CLAUDE.md` (where the `<!-- BEGIN FLOW-NEXT -->` template block lives, OR the project guide's command count)
   - `plugins/flow-next/README.md` (skills/commands table + count)
   - `~/work/mickel.tech/app/apps/flow-next/page.tsx` (commands array + lede count + FAQ if applicable) — **maintainer-only; external contributors skip per the contributing guide**

8. **CHANGELOG entry** under the appropriate `[flow-next X.Y.Z]` block describing what the skill does.

9. **Smoke test** if the skill has any flowctl plumbing (atomic file writes, schema additions). Pure-skill additions (markdown-only) get verified by manual invocation in a real session.

## Reference

This checklist captures the lessons from the 0.34.0 → 0.37.0 era when (a) 4 user-facing skills (resolve-pr, prospect, audit, memory-migrate) silently shipped to Codex without UI metadata, and (b) several skills shipped with inline cross-platform tables (`AskUserQuestion` / `request_user_input` / `ask_user`) that polluted the agent's context. Both fixed in 0.37.1. Don't repeat them.

# Adding a new user-facing skill (checklist)

When adding a new `/flow-next:<name>` skill, every step below MUST be done. Skipping any creates silent Codex degradation that won't surface for releases.

1. **Canonical skill** at `plugins/flow-next/skills/flow-next-<name>/SKILL.md` (+ `workflow.md` / `phases.md` as needed). Frontmatter: `name`, `description`, `user-invocable: false` (default for slash-only skills), `allowed-tools`.

2. **Slash command** at `plugins/flow-next/commands/flow-next/<name>.md` (mirror existing `audit.md` / `prospect.md` shape).

3. **Tool names in canonical = Claude-native** — write `AskUserQuestion`, `Task`, etc. directly. NO inline cross-platform tables. If you reference these tools, optionally add a parenthetical "(`sync-codex.sh` transforms `AskUserQuestion` into a plain-text numbered-prompt instruction for Codex)" for maintainer clarity — sync strips it from the Codex mirror. The Codex mirror never calls `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694).

4. **`scripts/sync-codex.sh` `generate_openai_yaml` call** added in the appropriate section (workflow blue `#3B82F6`, review red `#EF4444`, utility amber `#F59E0B`). Include display name, short description, brand color, explicit `false` for `allow_implicit_invocation`, optional default prompt.

5. **`scripts/sync-codex.sh` `REQUIRED_OPENAI_YAML_SKILLS` array** updated to include the new skill name. Validation will fail otherwise.

6. **Run `./scripts/sync-codex.sh`** — verify zero errors, all REQUIRED skills have `agents/openai.yaml`, and the Codex mirror has the rewritten tool names. Commit the regenerated `plugins/flow-next/codex/` directory.

7. **Commands list** updated in:
   - `CLAUDE.md` (where the `<!-- BEGIN FLOW-NEXT -->` template block lives, OR the project guide's command count)
   - Root `README.md` — the "Commands" table is the canonical user-facing surface (plugin `plugins/flow-next/README.md` is now a thin stub pointing at the root)
   - `~/work/mickel.tech/app/apps/flow-next/page.tsx` (commands array + lede count + FAQ if applicable) — **maintainer-only; external contributors skip per the contributing guide**

8. **CHANGELOG entry** under the appropriate `[flow-next X.Y.Z]` block describing what the skill does.

9. **Smoke test** if the skill has any flowctl plumbing (atomic file writes, schema additions). Pure-skill additions (markdown-only) get verified by manual invocation in a real session.

## Backend-split workflow.md (heuristic)

When a skill's `workflow.md` carries backend-specific content (RP / Codex / Copilot, or parallel-vs-serial dispatch), split it so only the active backend's content enters the agent's context per invocation.

**Heuristic — split when divergent content ≥ 50 lines.** Smaller divergences stay inline; extracting them costs more in maintenance (extra files, sync-codex rewrites, link drift) than they save in context.

**Canonical 4-file shape** (when split is warranted):

```
skills/flow-next-<name>/
  SKILL.md            # routing table: BACKEND → workflow-<backend>.md
  workflow-common.md  # backend-detection + shared phases (gated deep/validator/walkthrough if applicable)
  workflow-rp.md      # RepoPrompt-only
  workflow-codex.md   # Codex CLI-only
  workflow-copilot.md # GitHub Copilot CLI-only
```

SKILL.md routing block (canonical pattern in `flow-next-impl-review/SKILL.md`): `BACKEND=codex` → `workflow-codex.md`, etc., with explicit "Do not load the other two."

**Landed examples** (fn-48):
- `flow-next-spec-completion-review` (commit `b2f6f0e`) — workflow.md 645 → 4 files; RP-prompt template (~430 lines) isolated to `workflow-rp.md`.
- `flow-next-impl-review` (commit `06f6e6f`) — workflow.md 1126 → 4 files; `workflow-common.md` 565 LOC (over the ≤500 target, accepted vs duplicating gated phases). Auxiliary `deep-passes.md` / `walkthrough.md` untouched (already cross-backend).
- `flow-next-resolve-pr` — **inline-kept**: divergence is one ~22-line Phase 5 (parallel-vs-serial dispatch); below threshold.

**sync-codex.sh impact:** the RP-warning injector (line 365-378) auto-prefers `workflow-rp.md` when present, falling back to monolithic `workflow.md`. No sync edits needed unless new tool-name references are introduced (see memory entry `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18`).

## Reference

This checklist captures the lessons from the 0.34.0 → 0.37.0 era when (a) 4 user-facing skills (resolve-pr, prospect, audit, memory-migrate) silently shipped to Codex without UI metadata, and (b) several skills shipped with inline cross-platform tables (`AskUserQuestion` / `request_user_input` / `ask_user`) that polluted the agent's context. Both fixed in 0.37.1. Don't repeat them.

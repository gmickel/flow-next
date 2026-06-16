---
satisfies: [R2]
---

## Description
Resolve the `/flow-next:export-context` consistency bug and confirm the doc-edit → sync → gate loop is clean. `flow-next-export-context/SKILL.md` advertises a `/flow-next:export-context` slash command and gives slash-command usage examples, but no `commands/flow-next/export-context.md` exists, so the command cannot resolve. **Prefer the docs-only fix** (reword the SKILL.md so it no longer advertises a slash command — describe it as phrase-triggered like `flow-next-deps`/`flow-next-rp-explorer`/`flow-next-worktree-kit`, which also have no command file). Only add a command file if a real `/flow-next:export-context` command is genuinely wanted — that is NOT docs-only and triggers a version bump + full count sweep.

Also run the count-invariant verification (memory: skill/command counts live on README + 3 JSON manifests) so this task proves the editing discipline before .2+ touch the high-traffic index files.

**Size:** S/M
**Files:** `plugins/flow-next/skills/flow-next-export-context/SKILL.md`; conditionally `plugins/flow-next/commands/flow-next/export-context.md` (only if adding the command); regenerated `plugins/flow-next/codex/**` (via sync, do not hand-edit).

## Approach
- Compare `flow-next-export-context/SKILL.md` trigger prose against a phrase-only skill (`flow-next-deps/SKILL.md`, `flow-next-rp-explorer/SKILL.md`) and match that pattern.
- After editing any synced file, run `./scripts/sync-codex.sh` and confirm `git diff --stat` shows only the regenerated mirror, then `bash scripts/ci_test.sh`.
- If (and only if) adding a command file: follow `agent_docs/adding-skills.md` (three-edit rule) and sweep counts per the memory grep below.

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-export-context/SKILL.md` — the inconsistent advertisement (lines ~3, ~30-31)
- `plugins/flow-next/skills/flow-next-deps/SKILL.md` — reference phrase-only trigger wording
- `agent_docs/adding-skills.md` — three-edit rule (only relevant if adding a command)
- `scripts/ci_test.sh` — the R17 + smoke gate that must stay green

**Optional** (reference as needed):
- `scripts/sync-codex.sh` — Codex mirror regeneration

## Key context
- Memory `skill-adding-version-bump-leaves-stale`: if the skill/command set changes, sweep counts: `grep -rn "[0-9]\+ skills\|[0-9]\+ commands\|Twenty-" .claude-plugin/ .agents/ plugins/flow-next/.claude-plugin/ plugins/flow-next/.codex-plugin/ README.md plugins/flow-next/README.md`.
- CLAUDE.md: pure docs = no version bump; adding a command IS a plugin change = version bump.

## Acceptance
- [ ] The `/flow-next:export-context` advertisement is consistent: either a working command file exists OR the SKILL.md no longer advertises a slash command.
- [ ] `./scripts/sync-codex.sh` regenerates the mirror with no parity drift; `bash scripts/ci_test.sh` passes.
- [ ] If the skill/command set changed, every count surface (README + 3 manifests) is swept and consistent; version bumped only if a command was added.

## Done summary
Landed via PR #175 (commit 669fba2) — GitHub docs overhaul. Spec/task scaffold was never committed; deliverables shipped without flow bookkeeping. Closing retroactively.
## Evidence
- Commits:
- Tests:
- PRs:
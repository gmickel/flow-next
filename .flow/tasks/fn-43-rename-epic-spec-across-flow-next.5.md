---
satisfies: [R11, R12, R13]
---

## Description

Rename the `epic-scout` agent to `spec-scout` (file move + prose rewrite) and update every dispatcher that references it by name. Minor edits to `worker.md` and `quality-auditor.md` for any incidental "epic" prose. Update the agent registration entries in `scripts/sync-codex.sh` so the Codex mirror picks up the new name on the next regen (T13 runs the regen).

**Size:** S
**Files:**
- `plugins/flow-next/agents/epic-scout.md` -> `plugins/flow-next/agents/spec-scout.md`
- `plugins/flow-next/agents/plan-sync.md`
- `plugins/flow-next/agents/worker.md`
- `plugins/flow-next/agents/quality-auditor.md`
- `scripts/sync-codex.sh` (lines 31, 98, 281)

## Approach

- `git mv plugins/flow-next/agents/epic-scout.md plugins/flow-next/agents/spec-scout.md`. Rewrite frontmatter `name: epic-scout` -> `name: spec-scout`. Rewrite all 18 references in body (per repo-scout).
- `plan-sync.md` (18 epic refs): rewrite `epic-scout` -> `spec-scout` in dispatch references; rewrite "epic" -> "spec" prose.
- `worker.md` (3 refs), `quality-auditor.md` (1 ref): incidental prose updates.
- `scripts/sync-codex.sh`:
  - Line 31: `INTELLIGENT_SCOUTS="epic-scout ..."` -> `"spec-scout ..."`.
  - Line 98: persona mapping `epic-scout)` -> `spec-scout)`.
  - Line 281: rewrite rule `flow-next:epic-scout` -> `flow-next:spec-scout` for the underscore-vs-dash mirror naming.

## Investigation targets

**Required:**
- `plugins/flow-next/agents/epic-scout.md` -- frontmatter + body.
- `plugins/flow-next/agents/plan-sync.md` -- dispatcher references.
- `scripts/sync-codex.sh:31, 98, 281` -- specific lines per repo-scout.

**Optional:**
- Other skills that reference scout names (most use them via Task tool dispatch and do not hardcode names; verify via grep `epic-scout` repo-wide).

## Acceptance

- [ ] `git mv` plus content rewrite leaves no `epic-scout` references in `plugins/flow-next/agents/` or `plugins/flow-next/skills/` or `scripts/sync-codex.sh`.
- [ ] `plan-sync.md` dispatch references the new name.
- [ ] After T13 runs `sync-codex.sh`, the Codex mirror has `agents/spec-scout.toml` (no `epic-scout.toml`).
- [ ] Frontmatter `name:` field updated; `description:` field updated where it mentions epic.

## Done summary
Renamed epic-scout agent to spec-scout via git mv (preserves history); rewrote frontmatter, body prose, and dispatcher refs in plan-sync.md / worker.md / quality-auditor.md / flow-next-plan steps.md / scripts/sync-codex.sh (3 sites). Reviewer also caught a critical worker/plan-sync dispatch-contract mismatch (EPIC_ID -> SPEC_ID); fixed by updating phases.md (2 templates), flow-next-sync/SKILL.md, and sync-codex.sh:226 worker-template heredoc. Reverted flowctl CLI verbs in agent prose to legacy alias form (flowctl epics, tasks --epic) per T10 scope split — codex reviewer cannot verify alias availability outside diff.
## Evidence
- Commits: 225dc94, e73ad82, ab16f6d
- Tests: grep -rn 'epic-scout' plugins/flow-next/agents plugins/flow-next/skills scripts/sync-codex.sh, grep -rn 'EPIC_ID' plugins/flow-next/skills/flow-next-work plugins/flow-next/skills/flow-next-sync, flowctl codex impl-review fn-43-rename-epic-spec-across-flow-next.5 --base 1ab92af
- PRs:
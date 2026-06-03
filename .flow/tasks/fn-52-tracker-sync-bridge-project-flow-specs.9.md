---
satisfies: [R15]
---

## Description

Repo-local finalization: the Codex mirror, the plugin version bump, and the final cross-task integration review. Runs after .8 — `sync-codex.sh` rewrites depend on the skill prose being frozen across .2/.4/.5/.6. (The flow-next.dev docs site is now its own task, fn-52.11, because the hybrid id model makes it a broad cross-page pass, not a single page.)

**Size:** M
**Files:** `scripts/sync-codex.sh` (+ regenerated `plugins/flow-next/codex/**`), `plugins/flow-next/.claude-plugin/plugin.json` (+ `.codex-plugin/plugin.json`).

## Approach

- **Codex mirror:** add a per-skill rewrite block for `flow-next-tracker-sync` in `sync-codex.sh` — FLOWCTL prelude var rewrite (`:177-213`), `Task`→agent (`:220-318`), `AskUserQuestion`→numbered-prompt (`:406-630`) covering the R9 interactive-confirm + R11 queue-not-prompt constructs, agent-role map (`:103`). Regenerate `codex/`. **Audit before/after idempotency** (per the sync-codex.sh audit convention).
- **Version bump:** this is a code feature → bump `plugin.json` (repo + `.codex-plugin`). (CLAUDE.md docs-only rule does not apply — code shipped.) fn-52.11 mirrors this version on the docs site.
- **Final integration review:** run impl-review against `git merge-base HEAD main` (not the task-start commit) to catch cross-task drift across .1–.8 + .10. (flow-next.dev docs site → fn-52.11; mickel.tech → maintainer-only, also in fn-52.11.)

## Investigation targets

**Required:**
- `scripts/sync-codex.sh:103,177-213,220-318,406-630` — rewrite stages
- `plugins/flow-next/.claude-plugin/plugin.json` + `.codex-plugin/plugin.json` — version
- `~/work/flow-next.dev/` structure + `agent_docs/releasing.md` (docs-site changelog format)

**Optional:**
- `plugins/flow-next/codex/` — regenerated mirror target

## Acceptance

- [ ] `sync-codex.sh` rewrites the new skill correctly; codex mirror regenerated; before/after idempotency verified; the conflict-prompt path matches canonical `AskUserQuestion` semantics [R15]
- [ ] `plugin.json` version bumped (repo + codex) [R15]
- [ ] Final impl-review run against `git merge-base HEAD main` (cross-task drift across .1–.8 + .10)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

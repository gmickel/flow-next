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
Finalized the fn-52 tracker-sync bridge for the repo: registered the new `flow-next-tracker-sync` skill in `sync-codex.sh` (openai.yaml + REQUIRED list) and added a maintainer-breadcrumb strip rule, regenerated the byte-identical-idempotent Codex mirror (also picking up fn-52.6 lifecycle-skill edits that had never been mirrored), and bumped the plugin version 1.4.0→1.5.0 across all manifests + README + CHANGELOG. The final-integration impl-review (run against `git merge-base HEAD main`) reached SHIP after fixing one Major cross-task drift — `sync receipt`/`sync defer` were writing artifacts from raw tracker handles instead of canonicalizing them — plus stale doc/count fixes.
## Evidence
- Commits: cd56b13bfd77f614b52fec6f7b19ac6d88ef9f8e, 3b7d1113cea9ba29fa7ad2b5d80281ac448503b5, b188526393cbe11243b405dbf1fecfdd932ebbd2
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' — 790 pass, 2 skip, bash scripts/sync-codex.sh — all validators green; mirror byte-identical idempotent across 2 runs, flowctl validate --spec fn-52-tracker-sync-bridge-project-flow-specs — valid, 11 tasks, impl-review rp --base $(git merge-base HEAD main) — SHIP (NEEDS_WORK→SHIP, 4 findings fixed)
- PRs:
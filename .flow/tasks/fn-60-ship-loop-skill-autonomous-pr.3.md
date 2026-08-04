---
satisfies: [R11]
---

## Description

Release surfaces for `/flow-next:land` (1.14.0): repo docs, the confined auto-merge exception, manifests + committed Codex mirror, and the flow-next.dev flip from "in development" to shipped.

**Size:** M
**Files:** README.md, GLOSSARY.md, CLAUDE.md, plugins/flow-next/docs/README.md, plugins/flow-next/docs/ralph.md, CHANGELOG.md, 3 manifests, plugins/flow-next/codex/** (regen), ~/work/flow-next.dev: autonomous/land.mdx, autonomous/overview.mdx, src/lib/site.ts, astro.config.mjs, src/pages/index.astro, releases/changelog.mdx, package.json

## Approach

- Repo: README line 24 "Twenty-seven"→"Twenty-eight" + commands-table row + "Going autonomous?" third path; GLOSSARY new `Land` term + extend `Verdict` (LAND_VERDICT set); CLAUDE.md "No direct gh pr merge" rule gains the confined land exception sentence; docs/README.md index row; ralph.md host-driven-loop section third row + `/loop 30m /flow-next:land` recipe; CHANGELOG `[flow-next 1.14.0]`.
- Manifest count strings: `plugins/flow-next/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` "27 skills"→"28 skills" (+ commands 23→24); `.codex-plugin/plugin.json` `interface.longDescription` 27→28 skills. `bump.sh minor` for version lockstep (5 manifests + README badge).
- Mirror: `./scripts/sync-codex.sh` regen incl. new flow-next-land mirror; audit the R2-block placement memory entries (r2-ask-block-must-never-anchor / codex-mirror-audit) — land has no AskUserQuestion so expect zero R2 injections; verify.
- Site: land.mdx full flip to shipped doc (invocation, verdict grammar, gates, config keys, min-gh note); overview.mdx status row + section de-soon; BOTH navbars drop "(soon)"; landing index.astro loop-card `soon`→shipped tag; changelog entry per strict format; FLOW_NEXT_VERSION + package.json 1.14.0; `pnpm build` gate. Site commit held until tag per release flow.
- Optional follow-up noted for the human: ~/work/mickel.tech flow-next page commands array + resolve-pr FAQ line (separate repo, not gating).

## Investigation targets

**Required:**
- `agent_docs/releasing.md` — release runbook + docs-site changelog format
- `.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05` — manual count-string patching
- `~/work/flow-next.dev/src/content/docs/autonomous/land.mdx` + `overview.mdx` — current preview copy to flip

**Optional:**
- fn-59.3 commit 3465f89 — the 1.13.0 release-task shape to mirror

## Acceptance

- [ ] Repo docs updated (README counts/row/blurb, GLOSSARY Land+Verdict, CLAUDE.md exception, docs index, ralph.md row+recipe, CHANGELOG)
- [ ] Counts + versions lockstep at 1.14.0 across manifests + README badge; all tests + sync-codex validators green; committed mirror includes flow-next-land
- [ ] Site flipped: land.mdx shipped doc, overview row, both navbars, landing card, changelog entry, version refs; `pnpm build` green; commit held until tag
- [ ] No `(soon)` / "in development" references to land remain anywhere on the site

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: land docs + site autonomy story shipped with release 1.14.0. No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs:
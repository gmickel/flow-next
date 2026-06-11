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
1.14.0 release surfaces for /flow-next:land: repo docs (README 28-skills count + commands row + third autonomous path, GLOSSARY Land term + Verdict extension, CLAUDE.md confined merge-rule exception, docs index, ralph.md ship-loop recipe, CHANGELOG 1.14.0, flowctl.md land.*/land.merged config rows), manifests at 1.14.0 lockstep with 28-skills/24-commands counts, regenerated Codex mirror incl. flow-next-land (zero R2 injections), and the flow-next.dev flip to shipped (land.mdx full doc, overview row, both navbars, landing card, changelog, version refs — commits ff521e1+9aceb86, held unpushed until the release tag). Four codex impl-review fix rounds also hardened sync-codex /skills/ path rewriting + validator, land's transactional .flow close persistence, the fn-57 tracker dispatch grammar, centralized ledger writes, flake-vs-fix strike timing, and CI wiring for test_land_config.py.
## Evidence
- Commits: 19b880e0f892893e059b303dc791ef924eb23372, 34bb4489364d2fd7d601989d37cdb1023d2664fc, 4f7dfe4c4dcde6d326d8b9acab528d81248fa3f1, 07b7249cc10966745805a5807fb675c64e67442e, 1ac45453ac5f4573822eb826fd1180a4cc8da2eb
- Tests: for f in plugins/flow-next/tests/test_*.py; do python3 $f; done (all green, incl. test_land_config.py), bash -n scripts/sync-codex.sh && ./scripts/sync-codex.sh (all validators green incl. new /skills/-ref validator; byte-idempotent re-run), cd ~/work/flow-next.dev && pnpm build (61 pages, green), jq version lockstep check: 1.14.0 across 5 manifests + README badge, grep sweep: zero '(soon)'/'in development' land refs sitewide
- PRs:
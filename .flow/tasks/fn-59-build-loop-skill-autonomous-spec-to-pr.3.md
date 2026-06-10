---
satisfies: [R8, R9, R10]
---

## Description

Docs (repo + flow-next.dev), the Ralph-vs-pilot story, the hero autonomy pillar, Codex mirror regen, and the 1.13.0 release mechanics.

**Size:** M
**Files:** repo: `README.md`, `GLOSSARY.md`, `CLAUDE.md` (Where-to-look row), `plugins/flow-next/docs/README.md` + `docs/ralph.md`, 3 manifests' count strings, `CHANGELOG.md`, version files (bump.sh), `plugins/flow-next/codex/**` (regen incl. new pilot mirror + openai.yaml); site: `src/content/docs/skills/pilot.mdx` (new) + BOTH navbars + `ralph/*.mdx` cross-links + `src/pages/index.astro` hero `proofPillars` + changelog + `FLOW_NEXT_VERSION`/`package.json`
<!-- Updated by plan-sync: fn-59.1 added a new skill AND a new command (commands/flow-next/pilot.md) but left manifests at 1.12.0 counts. Count-string targets verified against actual files: skills 26→27, commands 22→23. Per-manifest: .claude-plugin/plugin.json description "21 subagents, 22 commands, 26 skills" → "...23 commands, 27 skills"; .claude-plugin/marketplace.json plugins[0].description same string → same bump; .codex-plugin/plugin.json carries "21 subagents, 26 skills" in interface.longDescription ONLY (top description has no counts) → "...27 skills" (no command count there). The README "Twenty-six"→"Twenty-seven" skills + commands-table row still hold; also bump the commands count if README states one. -->`

## Approach

- **Repo docs:** README — "Twenty-six"→"Twenty-seven" skills, commands table row, "Going autonomous?" blurb distinguishing Ralph (external shell loop, fresh sessions, overnight) from pilot (in-session single-tick, host `/loop`//`goal` driven); GLOSSARY — new `## Pilot`, `## Verdict` terms + one Ralph-contrast sentence in the existing `## Ralph` entry (FLOW_AUTONOMOUS lives inside those entries — don't over-mint terms); docs/ralph.md — "Host-driven loop vs Ralph" subsection (signals, receipts vs verdicts, when to use which); docs/README.md index row; CLAUDE.md Where-to-look row; 3 manifests' human count strings (memory: plugin.json + marketplace.json + .codex-plugin all carry counts).
- **Driver docs (the load-bearing page content):** how to drive pilot — Claude `/goal` (v2.1.139+; condition phrased against `PILOT_VERDICT=` grammar, e.g. "keep running /flow-next:pilot until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns"), `/loop` (v2.1.72+; 7-day expiry note), Codex `/goal` (opt-in `[features] goals = true`; plain-text objective — NO $skill-in-goal); unattended-rp caveat (use codex/copilot or --review=none overnight); caps live in the driver.
- **Site:** new `skills/pilot.mdx` (invocation, arg surface, verdict grammar, strikes/don't-thrash, drive recipes, Ralph contrast) registered in BOTH nav sources; `ralph/autonomous-mode.mdx`/`overview.mdx` cross-link; **hero**: add the autonomy pillar to `proofPillars` (data-array since fn-57.8 — one entry, e.g. glyph `↻` "Autonomous loop / Drain the backlog hands-free."), R10 decision = YES per maintainer's standing intent; changelog `### 1.13.0` strict format; version bumps.
- **Release:** `bump.sh minor` (1.12.0 → 1.13.0, all manifests lockstep) → `./scripts/sync-codex.sh` regen — .1/.2 registered + locally validated but deliberately did NOT commit `codex/**`; this task owns the committed mirror (new pilot mirror + openai.yaml; audit: R2 blocks land after complete sentences, splice anchors intact, REQUIRED_OPENAI_YAML_SKILLS satisfied) → CHANGELOG. `pnpm build` green; site commit separate + unpushed until the tag (release sequence owns pushes). RP-review note: run impl-review with `--base $(git merge-base HEAD main)` + full-file selection (memory: builder slices cause false positives on release tasks).

## Investigation targets

**Required:**
- `agent_docs/releasing.md` + `agent_docs/adding-skills.md` steps 4-9
- `~/work/flow-next.dev/src/pages/index.astro` proofPillars array + `src/lib/site.ts` navGroups + `astro.config.mjs` sidebar
- `plugins/flow-next/docs/ralph.md` — where the contrast subsection lands
- docs-scout's driver semantics (in spec §Resolved: Codex opt-in, version gates, transcript-blind validator)

**Optional:**
- `~/work/flow-next.dev/src/content/docs/skills/qa.mdx` — newest skill page as the shape template
- `.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03` — dual-nav rule

## Acceptance

- [ ] All repo docs above updated; counts consistent across README + 3 manifests; GLOSSARY terms land
- [ ] ralph.md + site ralph pages carry the host-driven-vs-Ralph contrast; pilot.mdx teaches the drive recipes with exact version/opt-in gates and the verdict-grammar conditions
- [ ] Hero shows the autonomy pillar; both navbars list pilot.mdx; slug-diff sanity passes; `pnpm build` green
- [ ] Mirror regenerated with pilot included (openai.yaml present, R2/anchor audit clean); CHANGELOG + 1.13.0 lockstep
- [ ] Site commit separate, unpushed until tag

## Done summary
1.13.0 release surfaces for /flow-next:pilot: repo docs (README Twenty-seven + commands row + two-path autonomy blurb, GLOSSARY Pilot/Verdict terms + Ralph contrast, docs/ralph.md "Host-driven loop vs Ralph" subsection with drive recipes and version gates, docs index + CLAUDE.md rows), manifest count sweep (21 subagents / 23 commands / 27 skills), CHANGELOG 1.13.0, bump.sh minor lockstep, and the committed Codex mirror regen including the new pilot mirror (openai.yaml present, R2 audit clean — plus an is_negative_context hardening so the R2 ask block can never anchor in autonomous hard-error prose). flow-next.dev updated in a separate unpushed commit (5b806f4): new skills/pilot.mdx in BOTH navbars, ralph cross-links, seventh hero pillar "Autonomous loop", changelog entry, FLOW_NEXT_VERSION/package.json 1.13.0, pnpm build green. RP impl-review SHIP after 2 fix rounds; repo docs batch implemented via codex delegation (gpt-5.5/medium, class=success).
## Evidence
- Commits: 3465f89, 2550f95, 49496fb, 3ff66b5
- Tests: for f in plugins/flow-next/tests/test_*.py; do python3 $f; done (all green), ./scripts/sync-codex.sh (validation green: 28 skills, 21 agents, openai.yaml coverage incl. flow-next-pilot), cd ~/work/flow-next.dev && pnpm build (59 pages, green; site commit 5b806f4, unpushed until tag), jq parse + count grep across README + 3 manifests (27 skills / 23 commands / 21 subagents), version lockstep check: 1.13.0 across 5 manifests + README badge + site FLOW_NEXT_VERSION/package.json
- PRs:
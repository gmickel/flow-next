---
satisfies: [R1, R4, R5, R10]
---

## Description

mickel.tech flow-next page overhaul per Workstream C. Repo: ~/work/mickel.tech (Next 16 App Router, copy in const arrays, biome gate).

**Size:** L
**Files:** app/apps/flow-next/page.tsx (1445L, all copy in top const arrays), lib/releases.ts, app/apps/flow-next/flow-next-schematic.tsx (dead code decision), components/sections/atelier/sdlc-tools.tsx (reciprocal link exists - verify)

## Approach

Workstream C list 1-7: facts sweep (APP_DATA.version 1.14.0 -> current; "Twenty-three commands" -> 28+ skills; add Cursor backend + GitLab/Jira trackers; GPT-5.6 family / role labels; JSON-LD fix); hero + FAQ reframe on the claim hierarchy (hero line direction approved; cut "(0.39.0+)" changelog-museum tags; shorten pasted-release-note FAQ answers - JSON-LD quality); Prime section rebuilt to the 2.13.0 classification/verdict model (drop the % maturity ladder); NEW flexibility/orchestration section (menu framing + model-per-step, link flow-next.dev/cookbook + orchestration); lib/releases.ts fix (v0.38.1/retired repo/wrong logo -> current entry linking the docs-site changelog); credibility strip (anonymized-bold, cross-linking to https://flow-next.dev/proof/field-notes/ for the field evidence backing it) + cross-links to /sdlc and /expert; testimonial content REPLACED wholesale from agent_docs/testimonials.md - the live page's mangled/paraphrased quotes and invented handles are swapped for the manifest's verified GitHub-pool entries, not re-linked; the d7a4024 X set is EXCLUDED (fn-117.1: status ids fabricated - snowflake dates predate the repo, a duplicate id, all seven 404 against a resolving control) so do not attempt to restore mangled entries to their d7a4024 originals; delete-or-wire flow-next-schematic.tsx.
<!-- Updated by plan-sync: fn-117.1 used GitHub-pool-only manifest (d7a4024 recovery failed - fabricated status ids, all 404) not d7a4024-restored links -->
<!-- Updated by plan-sync: fn-117.6 shipped the field-notes page at flow-next.dev/proof/field-notes/ (was undetermined at plan time) -->
EN/DE: the flow-next page is EN-only const arrays - confirm; touch messages/*.json only if shared strings change.

## Acceptance

- [ ] Zero stale facts (version/counts/backends/trackers/models); JSON-LD version current (R10)
- [ ] Hero leads with the accuracy claim (R1); flexibility section present; Prime section matches 2.13.0 reality
- [ ] All testimonial links resolve to the verified manifest entries (R5); credibility strip anonymized-bold (R4)
- [ ] /sdlc + /expert cross-links live; releases.ts current; bun x biome check + build green (R10)

## Done summary
mickel.tech flow-next page overhauled to the fn-117 claim hierarchy (commit 3a0c65c in ~/work/mickel.tech, committed there per site conventions): hero/metadata/OG image lead with "Agents generate. Flow-Next proves."; full facts sweep (JSON-LD version 2.20.0, 28 skills, 22 subagents with correct Haiku/Sonnet/Opus tiers, 4 review backends incl. Cursor, 4 trackers incl. GitLab/Jira, role labels replacing stale GPT-5.5 refs); testimonials replaced wholesale from the verified GitHub-pool manifest (agent_docs/testimonials.md; Novotny #111 lead, fabricated X set fully removed); credibility strip added (anonymized-bold field evidence -> flow-next.dev/proof/field-notes/, plus /sdlc and /expert consulting cross-links); new Flexibility section (menu-not-a-rail + model-per-step, linking doctrine/cookbook/orchestration); Prime section rebuilt to the 2.13.0 classification/verdict model with the % maturity ladder dropped; FAQ answers shortened for JSON-LD quality with all changelog-museum version tags cut; lib/releases.ts fixed (v2.20.0, correct logo, docs-site changelog link, EN/DE parity kept) and lib/apps.ts card refreshed; dead flow-next-schematic.tsx deleted (631 lines, never imported). sdlc-tools.tsx reciprocal links verified present (flow-next.dev + GitHub), untouched. Page confirmed EN-only const arrays. biome + build green; PSVI and client-name boundary greps clean.
## Evidence
- Commits: mickel.tech@3a0c65c459a224a973c3355a5caed5e7e322e6b2
- Tests: baseline: green (cd ~/work/mickel.tech && bun x biome check && bun run build, suite_rc=0 pre-edit; mickel.tech base 00acefe2668c3acd40fe89131401ed3aacf79be8; gate check --gate microsite-build: RUN, no honorable receipt), cd ~/work/mickel.tech && bun x biome check && bun run build (suite_rc=0 post-change; green receipt recorded via flowctl gate receipt --gate microsite-build), grep -ri 'PSVI|Velocity Index' over flow-next.dev/src + mickel.tech/app/apps/flow-next + README.md + plugins/flow-next/docs (clean, exit 1, pre+post edit), grep -riwf ~/.claude/flow-next-client-names.txt over the same trees (clean, exit 1, pre+post edit), stale-fact sweep grep (1.13/1.14/0.39/0.40 tags, GPT-5.5, Twenty-three, x.com testimonial handles, maturity-% ladder) over page.tsx + opengraph-image.tsx + releases.ts + apps.ts -> empty (exit 1), flowctl gate classify --base ac139ed60071ce883d2fea07f1f376d1c0dca1b5 -> TIER_B docs-only (flow-next repo side carries task-tracking files only; all code changes live in mickel.tech)
- PRs:
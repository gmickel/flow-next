---
satisfies: [R1, R2, R4, R5, R6]
---

## Description

GitHub front door rework per Workstream A - the highest-leverage adoption surface.

**Size:** L (split candidate at work time if the hero asset drags: asset production may land as a follow-up commit)
**Files:** README.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/platforms.md, plugins/flow-next/docs/README.md, CODE_OF_CONDUCT.md (new), assets/ (social preview + hero), repo settings via gh api where possible

## Approach

Work the spec's Workstream A list 1-10 in order. Key mechanics:
- Social preview: produce assets/social-preview.png (1280x640, tagline + pipeline, site design language); UPLOAD IS MANUAL (GitHub has no API) - end the task with an explicit one-line instruction for the maintainer.
- Hero: asciinema-style terminal capture of a real plan->work->review SHIP->make-pr run ending on a receipt (record against a fixture repo; gif/svg <5MB). If recording tooling is unavailable, ship a polished static hero and file the gif as a follow-up note - do not block.
- Hero line: "Agents generate. flow-next proves." leads; "ship like engineers - not slot machines" stays as secondary.
- "The pipeline is a menu" section: ~15 lines from the recipe inventory (cite cookbook once .5 lands - use flow-next.dev/cookbook as forward link).
- Testimonials from agent_docs/testimonials.md ONLY (all linked).
- Enterprise strip: anonymized, BOLD statements per Decision 5.
- Community profile: `gh api` for Discussions enable + topics check; CODE_OF_CONDUCT.md (Contributor Covenant); note Wiki disable as manual step if API lacks it.
- Consistency sweep per audit list (18-vs-22 commands in teams.md L451, 20-vs-21 agents platforms.md L86/L129, marketplace URL mismatch platforms.md L9, model ids -> role labels across docs).
- PRESERVE VERBATIM: "Why this exists" narrative, seven tenets table.

## Investigation targets

**Required:**
- README.md current full read; the GitHub audit findings in fn-117 Workstream A
- agent_docs/testimonials.md (from .1)
- plugins/flow-next/docs/orchestration.md L11-20 + L83-112 (menu-section source material)

## Acceptance

- [ ] README: hero line + above-fold visual + menu section + linked testimonials + enterprise strip + proof badges; "Why this exists" byte-identical (R1, R2, R4, R5, R6)
- [ ] Community profile complete (Discussions, CoC); manual steps (social preview upload, wiki) listed in the done summary
- [ ] Consistency sweep verified by grep (no 18-command claims, no bare gpt-5.5 in docs prose outside dated examples)
- [ ] docs-linkcheck workflow green

## Done summary
GitHub front door reworked per Workstream A: README leads with "Agents generate. flow-next proves." + above-fold plan screenshot + proof badges (stars/3-OS CI/dynamic release/awesome); new "The pipeline is a menu, not a rail" section; testimonials rebuilt GitHub-pool-only (all linked, Novotny #111 lead - excluded X set removed); anonymized-bold enterprise strip; quick-start de-frictioned (setup-refresh below happy path, Grok to platforms.md pointer, stages in details blocks); real PR-body screenshot from merged PR #215; CODE_OF_CONDUCT.md (Contributor Covenant 2.1); Discussions ENABLED + Wiki DISABLED via gh api; consistency sweep (teams.md 22 commands + role-label backend examples, platforms.md marketplace URL + 22 agents + stale review-default id, README 22 agents, prime index row de-jargoned). "Why this exists" + tenets byte-identical.

MANUAL STEP (maintainer): upload assets/social-preview.png at Settings -> General -> Social preview (GitHub has no API for this).
Follow-ups noted: asciinema hero gif (static hero shipped per task fallback); 4 pre-existing broken relative links in flow-next-interview/flow-next-capture reference files (outside the CI linkcheck gate's effective scope); awesome-list upstream entry still cites the old repo name (upstream correction PR candidate).
## Evidence
- Commits: b231944a44c85d7fa04b78633721c5e53d3c47da
- Tests: baseline: green (boundary greps clean pre-edit, exit 1; spec Quick commands define no repo test suite - other-repo builds untouched by this task), python3 -m unittest discover -s plugins/flow-next/tests -q (1883 tests OK, skipped=3; gate receipt b231944a-unittest), grep -ri 'PSVI|Velocity Index' <all fn-117 surfaces> -> clean (exit 1), grep -riwf ~/.claude/flow-next-client-names.txt <all fn-117 surfaces + CODE_OF_CONDUCT + agent_docs> -> clean (exit 1), lychee --offline (docs-linkcheck workflow args + CODE_OF_CONDUCT.md) -> 0 errors; changed-files pass (README, CoC, teams, platforms, docs/README) -> 0 errors, grep '18 command|all 18' README+docs -> clean; excluded X-set names absent from README (grep clean), diff of '## Why this exists' through tenets table vs base commit -> byte-identical
- PRs:
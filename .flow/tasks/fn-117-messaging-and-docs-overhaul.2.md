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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

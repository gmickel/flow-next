---
satisfies: [R13, R14, R15]
---

## Description

Ship the self-improving story: a dedicated docs page (flow-next.dev + git-docs counterpart), the STRATEGY.md "self-improving through normal work" track, and the hero pillar grid redesign adding "Self-improving" — executed with the frontend design plugin.

**Size:** M
**Files:** repo: `STRATEGY.md`, `plugins/flow-next/docs/` (new self-improving page + README index row); site (`~/work/flow-next.dev`): new `src/content/docs/` page, `src/lib/site.ts` navGroups, `astro.config.mjs` sidebar, hero component (landing page pillar grid), changelog page

## Approach

- **Docs page (R13):** one page, both surfaces — "the system gets better as you use it." Cover the compounding surfaces with concrete loops: **memory** (bug/knowledge tracks, Ralph auto-capture, audit lifecycle), **glossary** (prime seeds → interview + capture add → plan/work/review read → audit prunes), **decision records**, **strategy** (drift surfacing in plan/capture). Frame the principle explicitly: improvement through normal work, never a manual compound/refresh ceremony. Git docs: `plugins/flow-next/docs/self-improving.md` + a row in `docs/README.md` index. Site: new `.mdx` page + **BOTH navbars** (`src/lib/site.ts` navGroups AND `astro.config.mjs` sidebar — the two-sources rule; a page in only one silently vanishes from the rail).
- **STRATEGY.md (R14):** add a `### Self-improving through normal work` track under `## Tracks` — the system compounds (memory, glossary, decisions, strategy) as a side-effect of normal use; explicitly NOT via manual ceremonies. Update `last_updated`. Keep the generator frontmatter intact (file is owned by flow-next-strategy; a careful direct edit is sanctioned here by the spec).
- **Hero pillar (R15):** add a sixth pillar — "Self-improving / Compounds as you work" (final copy at implementer's judgment, match the existing terse two-line register: ▣ Spec-driven / Intent survives the chat. etc.) — and **redesign the grid so six fit cleanly AND the layout stays extensible** (the loop chain will add more later). **MUST use the frontend design plugin for this work** (per maintainer instruction + global frontend-aesthetics rule). Avoid generic-AI layout; respect the site's existing type/palette system.
- **Gate:** `cd ~/work/flow-next.dev && pnpm build` green. Site commits land separately in the flow-next.dev repo. The repo-side changelog/version mechanics stay in fn-57.5 (which depends on this task).

## Investigation targets

**Required:**
- `~/work/flow-next.dev/CLAUDE.md` — navigation two-sources rule, changelog format, design conventions
- `~/work/flow-next.dev/src/lib/site.ts` + `astro.config.mjs` — both nav sources
- The hero/landing component (locate the pillar grid markup — search for "Spec-driven" / "Re-anchored")
- `STRATEGY.md` — current track structure + frontmatter
- `plugins/flow-next/docs/README.md` — index format for the new page row

**Optional:**
- `plugins/flow-next/docs/memory-schema.md`, `docs/glossary.md`, `docs/strategy.md` — source material to link, not duplicate

## Acceptance

- [ ] Self-improving page exists on flow-next.dev AND in `plugins/flow-next/docs/`, covering memory / glossary / decisions / strategy loops + the no-manual-ceremony principle, cross-linked rather than duplicating subsystem docs
- [ ] Page registered in BOTH navbars (navGroups + sidebar); slug-set diff sanity check passes
- [ ] STRATEGY.md carries the new track; frontmatter + other tracks untouched; `last_updated` bumped
- [ ] Hero grid shows six pillars incl. Self-improving, redesigned to fit + extensible; frontend design plugin used for the design work; no regression on mobile breakpoints
- [ ] `pnpm build` green; site changes committed separately in flow-next.dev

## Done summary
Shipped the self-improving story across both repos: plugins/flow-next/docs/self-improving.md (+ README index row) and STRATEGY.md gained the "Self-improving through normal work" track in flow-next; flow-next.dev gained /strategy/self-improving (registered in BOTH navbars) and a redesigned hero pillar grid — six pillars including "Self-improving / Compounds as you work." in an extensible 3-column auto-wrapping capability index (frontend-design plugin direction, existing type/palette, mobile breakpoints verified). Site changelog/version deferred to fn-57.5 per the don't-advertise-unreleased-versions rule.
## Evidence
- Commits: 3038897359d785a0fda9ead02caec03e84d197aa, flow-next.dev:94990d26a908d8eaa84038bdbf19b94c67412f95
- Tests: cd ~/work/flow-next.dev && pnpm build (green, 58 pages), slug-set diff astro.config.mjs vs site.ts navGroups (only install/introduction astro-only, as intended), visual QA via agent-browser on pnpm preview: 1512px / 1100px / 700px / mobile — six pillars render, no overflow, rail active state OK, relative cross-link existence check on docs/self-improving.md
- PRs:
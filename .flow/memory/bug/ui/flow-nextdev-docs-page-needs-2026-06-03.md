---
title: flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro
date: "2026-06-03"
track: bug
category: ui
module: src/lib/site.ts
tags: [flow-next.dev, docs-site, starlight, navigation, navGroups, DocsRail, fn-52]
problem_type: ui
symptoms: New Starlight docs page builds green and is URL-reachable but invisible in the rendered left rail
root_cause: "Custom DocsRail renders navGroups from src/lib/site.ts, not the Starlight sidebar array in astro.config.mjs; only the latter was updated"
resolution_type: fix
---

## Problem
On the flow-next.dev docs site, adding a new Starlight docs page (`teams/tracker-sync.mdx`) requires registering it in TWO independent navigation sources, not one. The obvious surface — the Starlight `sidebar` array in `astro.config.mjs` — is NOT the live docs navigation. The custom rail in `src/components/DocsRail.astro` iterates `navGroups` from `src/lib/site.ts` (wrapped by `StarlightSidebar.astro`, which Starlight uses as the Sidebar override). A page registered only in `astro.config.mjs` builds green and is reachable by URL, but is INVISIBLE in the rendered left rail on every page.

## What Didn't Work
Updating only the `astro.config.mjs` Starlight `sidebar` entry. `pnpm build` passed (the page rendered, links resolved), so the gap was silent — it only surfaced because the impl-review context builder flagged that `site.ts navGroups` Teams omitted the new page.

## Solution
Add the page to BOTH surfaces, in matching order:
1. `astro.config.mjs` Starlight `sidebar` → Teams group.
2. `src/lib/site.ts` `navGroups` → `["Teams", [["Collaboration", ...], ["Tracker Sync", "teams/tracker-sync"], ...]]` — this is what `DocsRail.astro` renders.
DESIGN.md states the rail must be identical on homepage and docs pages, with nav data sourced from `src/lib/site.ts` — `navGroups` is the authority; the Starlight `sidebar` config is effectively shadow nav.

## Prevention
When adding a docs page to flow-next.dev, grep BOTH `astro.config.mjs` (sidebar) AND `src/lib/site.ts` (navGroups) for the sibling page slug and add the new entry to each. A green `pnpm build` does NOT prove the page is in the visible nav — the custom rail can omit it silently.

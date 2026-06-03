---
satisfies: [R15]
---

## Description

flow-next.dev docs pass — **broader than a single page** because R16 introduces a *second user-facing id scheme* (tracker keys as resolvable handles). Both the tracker-sync bridge AND the hybrid id model ride into the public docs, so this touches every page that teaches how you reference a spec — not just a new tracker page. Separate repo (`~/work/flow-next.dev`), separate commit.

**Size:** M-L
**Files:** `~/work/flow-next.dev/**` (Starlight docs pages, `src/lib/site.ts`, `package.json`) — separate repo, separate commit.

## Approach

- **New tracker-sync page** — projection-not-coordination, discovery ceremony, sync state, transport ladder (MCP → GraphQL → no-op), lifecycle opt-in points, Ralph-safe conflict queue.
- **Hybrid id-model / handles explainer (the cross-cutting part Gordon flagged):** a dedicated section/page — synced specs are referenceable by their tracker key (`work wor-17`, `plan wor-17`, `show wor-17.1`); tracker-first canonical `wor-17-slug`, flow-first `fn-NN` + resolvable alias; ids never rename; one-team-per-repo.
- **Cross-page id edits (the larger pass):** every page that teaches spec referencing must stop implying `fn-NN` is the only id form — getting-started, the command / usage reference (`/flow-next:work <id>`, `/flow-next:plan <id>`, `/flow-next:interview <id>`), the teams / workflow walkthrough, and any examples that hardcode `fn-NN`. Add the optional, clearly-marked opt-in tracker-sync touchpoints to the lifecycle walkthrough — the **no-tracker path stays the documented default**, shown unchanged.
- **Release plumbing:** changelog entry in the strict per-release format (`agent_docs/releasing.md`), bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json` to match the plugin version from .9.
- **Gate:** `cd ~/work/flow-next.dev && pnpm build` green. Commit separately in the flow-next.dev repo.
- **mickel.tech** flow-next app page is **maintainer-only** (Gordon post-merge; contributor PRs skip it).

## Investigation targets

**Required:**
- `~/work/flow-next.dev/` structure — Starlight docs pages, `src/lib/site.ts` (`FLOW_NEXT_VERSION`), `package.json`
- `agent_docs/releasing.md` — "Docs-site changelog entry" strict format
- the repo docs from fn-52.8 (`docs/tracker-sync.md` + hybrid id model) — the source of truth to mirror

## Acceptance

- [ ] New tracker-sync page live (projection, discovery ceremony, sync state, transport ladder, lifecycle opt-in, Ralph-safe queue) [R15]
- [ ] Hybrid id-model / handles explainer added; **every spec-referencing page** (getting-started, command/usage ref, teams walkthrough, examples) updated so `fn-NN` is not implied as the only id form; `work wor-17` documented [R15]
- [ ] Lifecycle walkthrough pages gain opt-in tracker-sync touchpoints; no-tracker path stays the documented default (shown unchanged) [R15]
- [ ] Changelog entry (strict format) + `FLOW_NEXT_VERSION` + `package.json` bumped to match the plugin release [R15]
- [ ] `pnpm build` green; committed separately in the flow-next.dev repo [R15]
- [ ] mickel.tech flagged maintainer-only (not done by contributors) [R15]

## Done summary
Documented the tracker-sync bridge and the hybrid id model on flow-next.dev (1.5.0): a new Tracker Sync page (projection-not-coordination, discovery ceremony, transport ladder, opt-in lifecycle points, Ralph-safe queue), a "Spec & task ids" explainer (fn-NN vs tracker key wor-17, case-insensitive, ids-never-rename), cross-page id-referencing edits (introduction, commands, sync skill, teams/collaboration), tracker.* config docs, both nav surfaces (Starlight sidebar + custom navGroups rail), and a strict-format changelog entry with FLOW_NEXT_VERSION + package.json bumped to 1.5.0. Committed separately in the flow-next.dev repo; pnpm build green. Impl-review (rp): NEEDS_WORK → SHIP. mickel.tech flow-next app page left untouched (maintainer-only).
## Evidence
- Commits: d006857146ecb11d08d18b060197d6960fec4edc, e1d8bf8d514e724314336e56dc7e9e60a220ade6
- Tests: cd ~/work/flow-next.dev && pnpm build (astro check && astro build) — 0 errors, 52 pages
- PRs:
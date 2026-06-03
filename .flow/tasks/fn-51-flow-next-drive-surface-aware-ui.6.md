---
satisfies: [R8, R9]
---

## Description
Final integration: version bump, docs across three surfaces, and the user-facing migration note. **Review base = the full spec diff (merge-base), not just the last commit.**

- **Version bump** (matching) across `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` — real behavior change, not docs-only.
- **CHANGELOG.md** — entry for the rename + surface-aware ladder; **credit rayfernando-skills (Apache-2.0)** for the ladder design; note the Codex-side name changed from `agent-browser`.
- **README.md** — audit the "Twenty-four ... skills" count (stays 24 — rename not add; verify).
- **Migration / uninstall note (R9)** — `/flow-next:browser` is gone -> state the new name; an orphaned `browser`/`agent-browser` skill in a cached install auto-clears in ~7 days, or by clearing the stale cached marketplace directory under the Claude plugin cache path (`~/.claude/plugins/cache/<marketplace>`).
- **flow-next.dev** (`~/work/flow-next.dev`) — rename `src/content/docs/skills/browser.mdx` -> `flow-next-drive.mdx` (rewrite for the ladder); update nav `src/lib/site.ts` (~L46) and sidebar `astro.config.mjs` (~L345); add a `src/content/docs/releases/changelog.mdx` entry; run `pnpm build`.
- **mickel.tech** (`~/work/mickel.tech`) — flow-next app page is **maintainer-only**; note in handoff, do NOT edit here.

**Size:** M
**Files:** CHANGELOG.md; plugins/flow-next/.claude-plugin/plugin.json; plugins/flow-next/.codex-plugin/plugin.json; .claude-plugin/marketplace.json; .agents/plugins/marketplace.json; README.md; ~/work/flow-next.dev/src/content/docs/skills/flow-next-drive.mdx; ~/work/flow-next.dev/src/lib/site.ts; ~/work/flow-next.dev/astro.config.mjs; ~/work/flow-next.dev/src/content/docs/releases/changelog.mdx

## Investigation targets
**Required:**
- `agent_docs/releasing.md` — version-bump + docs-site changelog format
- `~/work/flow-next.dev/src/lib/site.ts` (~L46) + `astro.config.mjs` (~L345) — the Browser nav/sidebar entries
- `CHANGELOG.md:580-584` — prior `@browser`->`@agent-browser` rationale (superseded by this entry)

## Acceptance
- [ ] Version bumped consistently across both plugin.json + both marketplace.json
- [ ] CHANGELOG entry crediting rayfernando-skills; README skill-count verified
- [ ] Migration/uninstall note covers the old `browser`/`agent-browser` names + the cache-clear path
- [ ] flow-next.dev: page renamed + nav + sidebar + changelog updated; `pnpm build` passes
- [ ] mickel.tech flagged maintainer-only (not edited here)
- [ ] No stray `browser` skill references remain in repo docs

## Done summary
Final integration for fn-51: bumped flow-next 1.3.4 -> 1.4.0 across all four manifests, added the CHANGELOG entry for the browser -> flow-next-drive surface-aware driver ladder (crediting rayfernando-skills, Apache-2.0) plus the migration/uninstall note, verified the README skill count stays 24, and renamed the flow-next.dev docs page + nav/sidebar/changelog + version refs (committed separately, pnpm build green, not pushed).
## Evidence
- Commits: c08904065501502f164f69ec265dec53857fbc54
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (697 passed, 2 skipped), python3 -m py_compile plugins/flow-next/scripts/flowctl.py (OK), jq version assert: all 4 manifests = 1.4.0 (claude+agents marketplace.json, claude+codex plugin.json), grep -ni flow-next-drive CHANGELOG.md (entry present); grep rayfernando CHANGELOG.md (Apache-2.0 credit present), grep -rniE bare-browser sweep README/CHANGELOG/docs (only historical CHANGELOG hits, no dead browser-skill ref), scripts/sync-codex.sh re-sync: 25 skills/21 agents, all validation guards green, codex flow-next-drive present, no agent-browser/browser dir, cd ~/work/flow-next.dev && pnpm build (exit 0, 51 pages, /skills/flow-next-drive built, /skills/browser absent)
- PRs:
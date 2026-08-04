---
satisfies: [R4, R6]
---
# fn-164-session-scope-re-anchor-brief-one-call.2 Brief-first teaching: snippets, glossary, CLI docs, CHANGELOG, propagation

## Description
Teach brief-first re-anchor as the default cold-session step everywhere the list+read-everything pattern is currently taught; update CLI reference + glossary; stage CHANGELOG + docs-site; run propagation.

**Size:** S/M
**Files:** `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` (:4-8), `claude-md-snippet-plugin.md`, `agents-md-snippet.md`, root `CLAUDE.md` Flow-Next block, `plugins/flow-next/docs/flowctl.md` (new `### brief` beside `### anchor` ~:567-577), `GLOSSARY.md` (Re-anchoring entry), pilot/guide skill cold-session prose (`plugins/flow-next/skills/flow-next-pilot/SKILL.md`, `flow-next-guide`), `CHANGELOG.md`, codex mirror, `.flow/bin/*`

### Approach
- Replace the `flowctl list` + `show` re-anchor teaching in the three setup snippets with `flowctl brief` as step one (pointers to cat/anchor for depth). Stay inside `test_token_budgets.py` budgets — replace lines, don't append.
- Worker.md Phase 1 stays task-scope `anchor` (unchanged — workers have a task id); add brief only where cold sessions start: pilot tick opening, guide, setup snippets.
- GLOSSARY.md Re-anchoring entry gains the session-scope sentence.
- docs/flowctl.md `### brief` section: contents, budget, truncation, --json/--full; cross-link with `### anchor` both directions.
- CHANGELOG `## Unreleased` (user-outcome-first). Docs-site (`~/work/flow-next.dev`): update live reference pages for `brief` NOW, verify `pnpm build`; site's versioned changelog + version fields defer to the batched release (no unreleased format invented). Downstream walk (same workstream): follow `~/work/agent-instructions/downstream-properties.md` — docs-site, microsite, AIxSDLC guide, vault; per-property update-or-no-change evidence in done summary + PR body. Propagation: .flow/bin cp + rsync, gen_tracker_manifest, sync-codex.sh twice.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md:1-20` (+2 variants) — the pattern to replace
- `plugins/flow-next/tests/test_token_budgets.py` — budgets to stay inside
- `plugins/flow-next/docs/flowctl.md:560-580` — anchor section to sit beside

**Optional**:
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md` — where a tick orients cold
- `plugins/flow-next/agents/worker.md:45-56` — confirm Phase 1 stays untouched

### Key context
- fn-163 and fn-160 touch the same snippets/usage.md — second lander rebases against landed text.
- sync-codex.sh guards: new Claude-only phrasing may need a transform + hard-fail guard.

### Acceptance
- [ ] Setup snippets (x3) + root CLAUDE.md block teach brief-first cold-session re-anchor (R4)
- [ ] Pilot/guide cold-session prose points at brief; worker.md Phase 1 unchanged (R4)
- [ ] GLOSSARY Re-anchoring covers session scope (R4)
- [ ] `test_token_budgets.py` green (R4)
- [ ] docs/flowctl.md `### brief` documented + cross-linked (R6)
- [ ] CHANGELOG Unreleased; docs-site live pages updated + build green (versioned changelog deferred); downstream walk evidence per property; propagation + sync-codex x2 done (R6)
## Acceptance
- Brief-first re-anchor taught in setup snippets, pilot/guide cold-session prose, glossary; worker task-scope anchor untouched; token budgets pass (R4)
- CLI reference + CHANGELOG + docs-site staged; propagation and mirror regen complete (R6)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

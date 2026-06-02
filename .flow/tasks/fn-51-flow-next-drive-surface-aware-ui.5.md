---
satisfies: [R2, R7]
---

## Description
Fix the Codex mirror + cross-platform sync. In `scripts/sync-codex.sh`, the `browser` -> `agent-browser` rename block (~L148-173) is **mostly dead** once canonical is `flow-next-drive` (the Codex `@browser` collision disappears): drop the `mv`/`sed` name rewrite; **keep and rekey** the Codex-note preface insert to `flow-next-drive` (the awk referencing `$agent-browser` -> `$flow-next-drive`). The copy loop (~L133-138) auto-mirrors the renamed dir to `codex/skills/flow-next-drive/`.

Run a **two-pass rename sweep** (bare `browser` + variable-form) across canonical + mirror. If fn-51.1 added `AskUserQuestion`/`Task` to SKILL.md, add the corresponding sync rewrite rules (AskUserQuestion -> numbered-prompt; Task -> spawn_agent) and `allowed-tools` frontmatter. Regenerate and verify the mirror: `name: flow-next-drive`, no leftover `name: browser`/`agent-browser`, tables/fenced blocks survived the transform (known injection hazard). Update `plugins/flow-next/docs/sync-codex.md` if the transform rule changed. **Coordinate with fn-50** before editing `sync-codex.sh` (it also touches that file + plugin.json).

**Size:** M
**Files:** scripts/sync-codex.sh; plugins/flow-next/codex/skills/flow-next-drive/* (regenerated — never hand-edit); plugins/flow-next/docs/sync-codex.md (if transform changed)

## Investigation targets
**Required:**
- `scripts/sync-codex.sh:133-173` — copy loop + the rename block to drop/rekey
- `scripts/sync-codex.sh:182-184` (FLOWCTL rewrite), `:225+` (Task->agent), `:411-590` (AskUserQuestion->numbered) — only if the new SKILL.md uses those tools
- memory `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18` — table/fenced-block injection hazards
- memory `bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09` — two-grep-pass rule

## Acceptance
- [ ] `browser`->`agent-browser` rename block dropped/rekeyed; Codex-note preface rekeyed to `flow-next-drive`
- [ ] `sync-codex.sh` runs clean; mirror regenerates to `codex/skills/flow-next-drive/` with `name: flow-next-drive`
- [ ] No `name: browser` or `name: agent-browser` anywhere in the mirror; two-pass grep clean (bare + variable-form)
- [ ] Tables / fenced blocks intact in the transformed mirror
- [ ] `docs/sync-codex.md` updated if the transform rule changed

## Done summary
Fixed scripts/sync-codex.sh: dropped the dead `browser`→`agent-browser` mv/sed name-rewrite (canonical skill is now `flow-next-drive`; the copy loop mirrors that dir name and the `@browser` collision is gone), and kept + rekeyed the Codex Browser-Use preface to inject into `codex/skills/flow-next-drive/SKILL.md` (dropped the stale `$agent-browser` invocation, points users at the prose triggers). Regenerated the Codex mirror to `flow-next-drive` (`name: flow-next-drive`), verified two-pass grep clean, tables/fenced blocks intact, and byte-stable across re-sync.
## Evidence
- Commits: 44323f326afaa88ea2f2d41687c033da61145f94
- Tests: bash -n scripts/sync-codex.sh (syntax OK), bash scripts/sync-codex.sh (full sync clean: 25 skills, 21 agents, all 14 validation guards passed), mirror assert: name: flow-next-drive present; no codex/skills/*browser* dir; no name: browser|agent-browser in mirror, two-pass grep: bare browser + variable-form $browser/browser_skill — only legit compounds + OpenAI $browser-use prose remain, table/fence integrity: diff canonical-vs-mirror shows only generic sync normalization, tables byte-identical, fenced blocks balanced, idempotency: md5sum-of-md5sums byte-stable across 2nd sync; post-commit re-sync leaves no drift
- PRs:
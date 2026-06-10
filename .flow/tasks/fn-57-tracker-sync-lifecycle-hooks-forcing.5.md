---
satisfies: [R9]
---

## Description

Documentation (repo + flow-next.dev), Codex mirror regeneration, and the 1.11.0 release mechanics.

**Size:** M
**Files:** `plugins/flow-next/docs/tracker-sync.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/skills/flow-next-setup/templates/usage.md`, `CHANGELOG.md`, version files (via `scripts/bump.sh`), `plugins/flow-next/codex/**` (regenerated); site: `~/work/flow-next.dev/src/content/docs/teams/tracker-sync.mdx`, `src/content/docs/flowctl/commands.mdx`, changelog page, `src/lib/site.ts`, `package.json`

## Approach

- **tracker-sync.md**: "flowctl surface" (:133-135) gains `sync check` + `--event`; "Lifecycle sync points" (:94-113) gains the observability paragraph (event-tagged receipts, end-of-skill check, retro-fire, four-state summary vocabulary); add a "MISSING after retro-fire" recovery subsection (manual `/flow-next:tracker-sync push <spec-id>` once transport returns; read the `.flow/sync-runs/sync-*.json` note for the failure reason).
- **flowctl.md**: sync command table (:714-715) gains the `sync check` row (full flag set, OK/MISSING output contract, zero-cost inactive exit) + `--event` on the receipt row.
- **setup usage.md** (:122): `--event` on the receipt example + a `sync check` example line.
- **CHANGELOG.md**: keep-a-changelog entry `## [flow-next 1.11.0]` — Added (`sync check`, `--event`; prime glossary bootstrap; capture glossary writes; glossary read path in scouts/worker/reviews; self-improving docs page), Changed (work/capture/make-pr end-of-skill check + retro-fire; make-pr §4.6b; hero pillar grid), Fixed (linear-mcp.md UUID correction), Notes (Codex mirror regen, new test files + CI steps, STRATEGY.md self-improving track).
- **Release sequence** (agent_docs/releasing.md): `scripts/bump.sh` 1.10.2 → 1.11.0 (3 version files in lockstep) → `./scripts/sync-codex.sh` (skill edits from .2/.3/.4/.6/.7 do NOT auto-propagate — the committed `codex/` tree must be regenerated) → **mirror audit** per memory `audit-sync-codexsh-during-planning`: verify the work-phases splice anchors (`^### 3c. Spawn Worker`, `^### 3d.`) survived the .3 edits, and the new check blocks landed intact in `codex/skills/`.
- **Site** (per CLAUDE.md): `teams/tracker-sync.mdx` (same two sections as repo doc), `flowctl/commands.mdx` (sync check + --event), changelog page (strict per-release format: `### 1.11.0 — <title>` + bold one-liner + `<details>`), bump `FLOW_NEXT_VERSION` in `src/lib/site.ts` + `package.json`. NO new pages → no navbar changes (both navbars already carry tracker-sync + flowctl pages — verify, don't edit blindly). `pnpm build` gate before handoff; commit site separately.

## Investigation targets

**Required:**
- `agent_docs/releasing.md` — bump → sync-codex → CHANGELOG sequence + docs-site changelog format
- `plugins/flow-next/docs/tracker-sync.md:94-135`, `plugins/flow-next/docs/flowctl.md:691-722`
- `scripts/sync-codex.sh:124-138, 170-296` — copy + sed patches + work-phases splice (the anchors that must survive)

**Optional:**
- `~/work/flow-next.dev/CLAUDE.md` — navigation two-sources rule + changelog format
- `CHANGELOG.md:1-40` — recent entry style to match

## Acceptance

- [ ] tracker-sync.md, flowctl.md, usage.md updated as above, incl. the MISSING-recovery subsection
- [ ] CHANGELOG entry + version 1.11.0 via bump.sh (3 files lockstep)
- [ ] `sync-codex.sh` re-run; `codex/` tree committed; mirror audit confirms splice anchors + new blocks intact
- [ ] Site: tracker-sync.mdx + commands.mdx + changelog page updated, `FLOW_NEXT_VERSION` + package.json bumped, `pnpm build` green, committed separately in flow-next.dev
- [ ] No new pages → navbars untouched (verified both sources still list the edited pages)

## Done summary
Shipped the fn-57 docs + release task: tracker-sync.md / flowctl.md / setup usage.md gained the sync check + --event surface (incl. the MISSING-after-retro-fire recovery subsection), CHANGELOG got the [flow-next 1.11.0] entry, bump.sh took all manifests 1.10.2 → 1.11.0, the sync-codex.sh SECTION3C heredoc was fixed to carry the fn-57.7 glossary re-anchor line before regenerating + auditing the Codex mirror, and flow-next.dev got the 1.11.0 changelog entry + tracker-sync/configuration doc updates + version bumps (committed separately, pnpm build green, navbars untouched/verified). Nothing pushed — orchestrator owns pushes.
## Evidence
- Commits: 2f561b058ff337b13e10e52086dd1eb9017f6239, 9d63e42 (flow-next.dev)
- Tests: python3 -m unittest discover -s tests -q (1033 tests OK, 2 pre-existing skips), ./scripts/sync-codex.sh validation (all checks green via bump.sh), smoke: sync check in tracker-less tmp dir -> empty output, exit 0 (R8), smoke: sync receipt --event capture + sync check --events capture -> missing:[], --events makePr (fresh --since) -> MISSING:makePr, mirror audit: codex/skills/flow-next-work/phases.md §3c/§3d splice anchors intact, glossary re-anchor line at :227, work Phase 5 / capture Phase 6 / make-pr §4.6b+§5.7 / prime 5.5 blocks present, scout+worker .toml glossary read path present, cd ~/work/flow-next.dev && pnpm build (58 pages, green)
- PRs:
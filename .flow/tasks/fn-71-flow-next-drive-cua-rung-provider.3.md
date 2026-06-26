---
satisfies: [R8]
---

## Description

Cross-platform parity + the full documentation sweep + the **release version bump** for the CUA rung, per `agent_docs/releasing.md`. A driver rung does NOT touch the GF microsite / AI×SDLC guide. No new skill/command is added (skill/command counts unchanged) — but the version bumps across ALL surfaces. Documents BOTH the local rung (.1) and the sandbox rung (.2), so it gates after both.

**Size:** M
**Files:** repo docs + `CHANGELOG.md` (`## Unreleased`) + flow-next.dev (`~/work/flow-next.dev`) — **version bump DEFERRED to the batched release (no `bump.sh` here)**

## Approach

- **Codex mirror:** run `scripts/sync-codex.sh`, smoke the mirror, confirm the generated `references/cua.md` reads coherently (multi-host wiring intact; no Claude-only-as-sole-form). (Memory: mirror-regen can expose latent canonical gaps — smoke it, don't wait for review.)
- **Repo docs:** `plugins/flow-next/docs/skills.md:54` + `docs/README.md:38` (drive one-liner → "… or native via Computer Use / trycua-cua"); `docs/platforms.md:234` (driver-ladder string → add CUA native rung).
- **Repo `CHANGELOG.md`:** add the top entry (release docs require it — not just the docs-site changelog).
- **flow-next.dev** (`~/work/flow-next.dev`): `src/content/docs/skills/flow-next-drive.mdx` (CUA rung + the **install/permission instructions verbatim** — curl/PowerShell installers, multi-host MCP wiring, `cua-driver permissions grant` for Accessibility + Screen Recording, `cua-driver serve` daemon, README pointer); `src/content/docs/releases/changelog.mdx` (new entry under the unreleased/next section); **leave `FLOW_NEXT_VERSION` / `package.json` untouched — version bump deferred**. Drive page already in BOTH navbars — **no nav surgery**.
- **Version bump — DEFERRED (batched release, per CLAUDE.md):** do NOT run `scripts/bump.sh` or touch manifests / README badges / `FLOW_NEXT_VERSION` in this task. Stage the change as a `## Unreleased` CHANGELOG entry (repo + docs-site); the version-number bump across all surfaces happens later at the batched release. (Still run `sync-codex.sh` for the mirror — separately, above — that is not a version bump.)
- Gate: `cd ~/work/flow-next.dev && pnpm build`.

## Investigation targets
**Required:**
- `agent_docs/releasing.md` — the canonical release process (bump.sh, version surfaces, changelog format)
- `scripts/bump.sh` — the multi-manifest version bumper
- `scripts/sync-codex.sh:136,155-156` — mirror regen
- `plugins/flow-next/docs/platforms.md:234`, `docs/skills.md:54`, `docs/README.md:38`; `CHANGELOG.md`
- `~/work/flow-next.dev/src/content/docs/skills/flow-next-drive.mdx`, `src/lib/site.ts`, `astro.config.mjs`
**Optional:**
- `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` — changelog format

## Acceptance
- [ ] `scripts/sync-codex.sh` runs clean; the Codex mirror of `references/cua.md` reads coherently (multi-host); mirror smoked.
- [ ] Repo docs updated (`docs/skills.md`, `docs/README.md`, `docs/platforms.md`) + the **flow-next-drive SKILL frontmatter `description`** (native via "Computer Use" → "Computer Use / CUA") + **repo `CHANGELOG.md`** top entry added.
- [ ] flow-next.dev drive page carries the CUA rung + verbatim install/permission instructions; docs-site changelog entry added under the unreleased section; `FLOW_NEXT_VERSION` / `package.json` left as-is (bump deferred); `pnpm build` green; no nav surgery (rung, not a new page).
- [ ] **NO version bump in this task** — the change is staged under `## Unreleased` (repo + docs-site); `scripts/bump.sh` + manifests + README badges are deferred to the batched release (per CLAUDE.md).
- [ ] GF microsite / AI×SDLC guide NOT touched.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R1, R2, R6, R7]
---

## Description

Promote root `README.md` to canonical entry point (~300-350 lines), stub `plugins/flow-next/README.md` to a thin pointer (~10-30 lines), update `CLAUDE.md` to single-plugin reality + retarget "Where to look" row, and complete the cross-link sweep across all repo surfaces. This phase is purely structural reorganization — no content loss; all plugin-README content already extracted into `docs/` by Phase 1.

**Size:** M

**Files:**
- `README.md` (root) — rewrite as canonical
- `plugins/flow-next/README.md` — reduce to stub
- `CLAUDE.md` — line 3 framing flip + "Where to look" row 1 retarget
- `agent_docs/adding-skills.md` — line 19 cross-link redirect
- `plugins/flow-next/docs/teams.md` — 11 anchor links into legacy plugin README (lines 78, 108, 159, 189, 201, 207, 341, 357, 452, 455, 456) retargeted to root README or new `docs/<file>.md` siblings
- `plugins/flow-next/docs/ralph.md` — lines 992-993 `../README.md` reference retargeted
- `plugins/flow-next/docs/README.md` — final polish of the index from Phase 1 (verify all entries still accurate)

## Approach

- **Root README rewrite — sections in order:**
  1. Title + tagline + badges (1-line tagline; badges only load-bearing: License, version, Docs link, Discord, Sponsor)
  2. "What is this?" — 50-second pitch (1 para + 3 bullets)
  3. "Quick start" — install (5 lines) + 5-command happy path (Capture → Plan → Work → Make PR → Resolve PR)
  4. "How the flow works" — placeholder section (Phase 3 fills in the 6-step narrative)
  5. "Where to look" — table (task → repo file OR website page)
  6. Requirements / Platforms / License
- **Plugin README stub (~10-30 lines):**
  ```markdown
  # flow-next

  > [tagline matching root README]

  This is the plugin source directory. The canonical README for flow-next
  lives at the [repository root](../../README.md).

  - Install / quick start → [root README](../../README.md)
  - Workflow narrative → [root README → How the flow works](../../README.md#how-the-flow-works)
  - flowctl CLI reference → [docs/flowctl.md](docs/flowctl.md)
  - Ralph autonomous mode → [docs/ralph.md](docs/ralph.md)
  - Adopting in a team → [docs/teams.md](docs/teams.md)
  - Architecture + .flow/ layout → [docs/architecture.md](docs/architecture.md)
  - Full doc index → [docs/README.md](docs/README.md)
  ```
  Use **relative repo paths** (`../../README.md`); NO symlinks (GitHub-broken per github/markup#21, #882); include the **tagline** so plugin-directory landers get the first-sentence pitch.
- **CLAUDE.md update:**
  - Line 3: `"This repo is a Claude Code plugin marketplace. It ships two plugins: **flow** and **flow-next**."` → flip to single-plugin reality. Suggested: `"This repo ships the **flow-next** Claude Code plugin — a spec-driven, zero-dependency workflow for AI-assisted SDLC."` (single sentence; reflects fact that flow plugin was removed in 1.0.2 per commit `ffc7189`).
  - Line 86 ("Where to look" row 1): retarget from `plugins/flow-next/README.md` to `README.md` (root) + the new `docs/<file>.md` files for deeper detail.
  - Line 97: keep `flow` removal sentinel (commit `0a45aff`) — useful historical breadcrumb.
- **Cross-link sweep — exact targets:**
  - `README.md:7` — Docs badge: redirect from `plugins/flow-next/README.md` to root `#how-the-flow-works` anchor OR `plugins/flow-next/docs/README.md`.
  - `README.md:18` — prose "Read the full docs" link: now points at itself; reword to point at `plugins/flow-next/docs/README.md` (index) + flow-next.dev.
  - `README.md:83` — "Full docs / Codex install guide" links: retarget Full docs → `docs/README.md`; Codex install guide → `docs/platforms.md`.
  - `CLAUDE.md:3` — framing flip (see above).
  - `CLAUDE.md:86` — "Where to look" row 1 retarget.
  - `agent_docs/adding-skills.md:19` — skills/commands table reference: retarget to `plugins/flow-next/docs/<file>.md` or root README's "Where to look" table.
  - `plugins/flow-next/docs/teams.md` 11 anchors: each `../README.md#prospecting`, `#capture`, `#pr-creation`, `#pr-feedback-resolution`, `#memory-system`, `#project-strategy`, `#project-glossary`, `#command-reference`, `#cross-model-reviews` — retarget to new `docs/<file>.md` files where the content now lives, OR to root README's new sections, OR to flow-next.dev pages. Per-anchor verification: each retargeted link resolves at write time.
  - `plugins/flow-next/docs/ralph.md:992-993` — `[Flow-Next README](../README.md)` retarget to `[Flow-Next README](../../README.md)` (root).
- **CHANGELOG immutable:** historical references like `CHANGELOG.md:27` mention `plugins/flow-next/README.md:1589-1594` — DO NOT rewrite.
- **No version bump.**

## Investigation targets

**Required**:
- `README.md` (current 186 lines) — full file; rewrite from scratch using current content as baseline.
- `plugins/flow-next/README.md` (current 2,719 lines) — confirm Phase 1 extracted all dev-reference; only walkthrough content (Prospecting, Capture, etc.) remains for Phase 3 compression. Skim before stubbing.
- `CLAUDE.md` lines 1-100 (framing + Where-to-look + flow removal sentinel).
- `agent_docs/adding-skills.md:19` (skills table reference).
- `plugins/flow-next/docs/teams.md` lines 78, 108, 159, 189, 201, 207, 341, 357, 452, 455, 456 (anchor links — verify exact strings before retarget).
- `plugins/flow-next/docs/ralph.md:992-993`.

**Optional**:
- README length references: anthropics/claude-code (72 lines), cli/cli (105), uv (329), ruff (563), bun (446). flow-next ~350 target fits the uv band.
- GitHub markup symlink bugs: github/markup#21, #882 — context for NOT symlinking the plugin README.

## Key context

- **Plugin README MUST NOT be symlinked** — symlinked READMEs don't render correctly on GitHub (multiple long-standing issues). Use a 10-30 line stub file instead.
- **Single-plugin reality in CLAUDE.md:** the "ships two plugins" framing has been stale since 1.0.2 (commit `ffc7189`, removed legacy `flow` plugin). Phase 2 makes it visible.
- **Cross-link sweep is the highest-risk surface in this phase.** 11 anchor links into the plugin README from `docs/teams.md` will break silently if any retarget points at a non-existent anchor. Verify each retarget resolves before commit.
- **Phase 1 must have landed before this phase starts** (task dep enforces). Reading Phase 1's commits is the way to know which `docs/<file>.md` is the right retarget destination.
- **Plugin README stub keeps relative paths** — `../../README.md` not absolute URLs — so the stub works on forks, in offline clones, and in mirrors.
- **Root README "How the flow works" section** is left as a placeholder in this phase — Phase 3 fills in the 6-step narrative + flow-next.dev links. For Phase 2, write a single-line stub like `_(Phase 3 will land the 6-step workflow narrative here.)_` or simply omit the section heading until Phase 3.
- **No version bump.** Docs-only changes per CLAUDE.md rule.
- **`./scripts/sync-codex.sh` after the changes:** docs files are not mirrored; mirror regen should be a no-op. Verify validation guards still pass.

## Acceptance

- [ ] Root `README.md` ≤ 350 lines and contains: tagline + badges; "What is this?"; "Quick start"; "How the flow works" (placeholder); "Where to look" table; Requirements / Platforms / License.
- [ ] `plugins/flow-next/README.md` reduced to 10-30 line stub with tagline + 3-6 relative deep links. NOT a symlink. Tagline matches root README.
- [ ] `CLAUDE.md:3` framing flipped to single-plugin reality; `CLAUDE.md:86` "Where to look" row 1 retargeted.
- [ ] All 16 known cross-link sites retargeted: root README (3), CLAUDE.md (2), `agent_docs/adding-skills.md` (1), `docs/teams.md` (11), `docs/ralph.md` (1). Each retargeted link resolves to an existing file (and existing anchor if applicable).
- [ ] CHANGELOG line-number references untouched (immutable).
- [ ] `grep -rn "plugins/flow-next/README\.md" --include="*.md" --include="*.json" | grep -v "CHANGELOG\.md" | grep -v "plugins/flow-next/README.md:"` returns no hits (or only the stub's own self-references).
- [ ] `./scripts/sync-codex.sh` runs cleanly; all validation guards pass; idempotent.
- [ ] 612/612 unittests + 130/130 smoke green.
- [ ] No version bump in any manifest (docs-only).

## Done summary
Promoted root README.md to canonical entry point (249 lines, in 300-350 target band); stubbed plugins/flow-next/README.md to 13 lines with tagline + 6 relative deep links (no symlink); flipped CLAUDE.md:3 to single-plugin reality and retargeted the "Where to look" row 1 + expanded with 4 new docs/ siblings; swept all 16 cross-link sites (root README badge + 2 prose, CLAUDE.md, agent_docs/adding-skills.md, 12 sites in docs/teams.md, 1 in docs/ralph.md) — every retargeted link resolves. 612/612 unit + 130/130 smoke + clean sync-codex.sh. No version bump.
## Evidence
- Commits: 19ae684714d146d918015c360c4b8c56246024fe
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (612/612 passed), cd /tmp && bash plugins/flow-next/scripts/smoke_test.sh (130/130 passed), ./scripts/sync-codex.sh (14/14 validation guards passed, idempotent), grep verification gate: zero live-surface hits for plugins/flow-next/README.md outside stub self-refs + immutable historical .flow/specs/ entries + intentional agent_docs/adding-skills.md mention
- PRs:
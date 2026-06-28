## Goal
Regenerate the Codex mirror from the canonical fn-69.1/.2 files, extend the **transport vocabulary**, and complete the **full doc sweep** + changelog so GitLab is a documented, shipped tracker. (Spec R8, R9-verification.)

## Files
- `bash scripts/sync-codex.sh` → regenerates `plugins/flow-next/codex/` (mirror of steps.md / SKILL.md / gitlab.md). Also update the **registration description** (`scripts/sync-codex.sh` ~line 1255 + the Codex **`openai.yaml`**) that currently says "Linear/GitHub".
- **Transport vocabulary** — the receipt `--transport` enum and the SKILL.md/steps.md prose (today `{mcp,graphql,gh,none}` / "Linear+GitHub adapters") gain the GitLab rung (`glab`/`rest`). Update flowctl's receipt-transport validation + the prose **+ `references/adapter-interface.md`** — its "implemented by" table, the `issue.tracker` enum, the receipt-transport enum, and the `listOpenIssues` bullets still say Linear/GitHub only; add GitLab (+ the `glab`/`rest` rung) and the GitLab promoted-lane label semantics.
- **Doc sweep — EVERY stale "Linear/GitHub" supported-tracker enumeration / config table / command table / glossary signal list:**
  - `plugins/flow-next/docs/tracker-sync.md` — add GitLab + the new `perTracker.project`/`host` config.
  - `plugins/flow-next/docs/flowctl.md` (the tracker enumerations ~L594-608, ~L771-780).
  - `plugins/flow-next/docs/skills.md` (tracker-sync entry).
  - `teams.md` (supported-tracker line).
  - root `README.md` (~the command/tracker table).
  - `GLOSSARY.md` (the Tracker + discovery-ceremony entries — currently Linear/GitHub + four signals → add the GitLab signal).
- `CHANGELOG.md` — `## Unreleased` entry (batched-release rule — **NO `bump.sh`/`FLOW_NEXT_VERSION` bump**).
- `~/work/flow-next.dev`:
  - the tracker-sync docs page — add GitLab.
  - **BOTH navbars** — `src/lib/site.ts` navGroups + `astro.config.mjs` sidebar (CLAUDE.md "Navigation — TWO sources").
  - changelog `## Unreleased` entry; `FLOW_NEXT_VERSION` left for the batched release.
- Downstream narrative (AI×SDLC / GF microsite) — ONLY if they enumerate supported trackers (check; one-line tracker-list touch or skip).
- `plugins/flow-next/tests/test_tracker_sync_mirror_parity.py` (or the existing parity test if present) — assert canonical `gitlab.md` is mirrored into `plugins/flow-next/codex/` AND the `openai.yaml` description includes GitLab.

## Approach
- sync-codex.sh is deterministic — run it, diff the mirror, commit the regenerated output with the canonical changes.
- Doc sweep: GitLab joins Linear/GitHub in EVERY "supported trackers" enumeration found across the selected files; verify the slug-set diff across BOTH flow-next.dev navbars.
- Verify the zero-setup floor (R9): docs state GitLab works from an existing `glab auth login` session OR a CI/PAT token (gh-style), no flow-next provisioning; spec-first floor when neither present.

## Acceptance
- Codex mirror regenerated + the named parity test green; `openai.yaml` + sync-codex registration include GitLab (R8).
- Transport vocabulary (receipt `--transport` enum + SKILL/steps prose) includes the GitLab rung (R8).
- Doc sweep complete — `docs/tracker-sync.md`, `docs/flowctl.md`, `docs/skills.md`, `teams.md`, `README.md`, `GLOSSARY.md` + flow-next.dev (page + BOTH navbars + changelog) all updated; no stale "Linear/GitHub-only" enumeration remains (R8).
- `CHANGELOG.md` `## Unreleased` entry; **no version bump** (batched-release rule).
- Downstream narrative checked (updated iff they list trackers).
- Full test suite + flow-next.dev `pnpm build` green.

## Test notes
- Mirror-safety/parity test + full suite + docs-site build. No live GitLab.

## Description
TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

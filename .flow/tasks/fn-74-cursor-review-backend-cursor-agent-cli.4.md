---
satisfies: [R13]
---

## Description

Walk the full documentation chain so the shipped cursor backend is reflected everywhere — **no version bump** (stage under `## Unreleased`; the bump is a separate batched decision per CLAUDE.md). Note: the flow-next.dev review-backend **enumeration + a Cursor row already exist** (added earlier this session, marked *"coming next release"*) — this task **flips that row to shipped**, it doesn't build the scaffold from scratch.

**Size:** M
**Files:** repo docs + 3 downstream repos + vault

## Approach

Per R13's concrete target list:
- **Repo:** `plugins/flow-next/docs/flowctl.md` (cmd list + new cursor backend section), `README.md` (the 3 backend lists at ~L44/L253/L290), `GLOSSARY.md` (~L29 "Backends:" line), root `CHANGELOG.md` `## Unreleased`.
- **flow-next.dev** (`~/work/flow-next.dev`): `src/content/docs/review/workflow.mdx` — flip the Cursor row from "coming next release" to a shipped row + drop the coming-soon note; `review/receipts.mdx` (the `mode` field gains `cursor`); `install.mdx` if it enumerates backends; `releases/changelog.mdx`; bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json` **only at the batched release**, not here. Run `pnpm build`. Commit separately in that repo.
- **AI-x-SDLC** (`~/work/AI-x-SDLC-Starter-Kit`): `guides/flow-next.md` (~L65 "(RepoPrompt, OpenAI Codex, GitHub Copilot)" → add Cursor), `guides/code-review-tools-changelog.md`.
- **GrowthFactors** (`~/work/code-factory-package`): `spec/05-cross-model-review.md` (already lists Cursor — verify/tighten now that it's true), re-render `dist/gf.html` (+ `shd`/`shopfully`/`flooid`) and the bundled `~/work/AI-x-SDLC-Starter-Kit/resources/assets/code-factory-onboarding.html`.
- **Obsidian vault** (`~/Documents/GordonsVault/Spaces/Projects/flow-next`, not git): the cross-model-review / Skills Catalog / Release Timeline note(s).

## Investigation targets

**Required:**
- `plugins/flow-next/docs/flowctl.md`, `README.md` (L44/L253/L290), `GLOSSARY.md` (L29), `CHANGELOG.md`
- `~/work/flow-next.dev/src/content/docs/review/workflow.mdx` (Cursor row exists — flip), `review/receipts.mdx`, `install.mdx`, `releases/changelog.mdx`
- `~/work/AI-x-SDLC-Starter-Kit/guides/flow-next.md` (L65), `guides/code-review-tools-changelog.md`
- `~/work/code-factory-package/spec/05-cross-model-review.md`, `dist/gf.html`

## Key context

Downstream-doc currency is a CLAUDE.md standing requirement — walk repo docs → flow-next.dev → GF + AI×SDLC + vault. The vault lags most; don't skip it. flow-next.dev changelog/version bump only happens at the batched release, not per-spec.

## Acceptance

- [ ] Repo docs updated — `flowctl.md`, `README.md` (3 lists), `GLOSSARY.md`, `CHANGELOG.md` `## Unreleased`; **no `bump.sh`** (R13)
- [ ] flow-next.dev: Cursor row flipped coming→shipped; `receipts.mdx` `mode` + `install.mdx` enumeration updated; changelog entry; **no `FLOW_NEXT_VERSION` / `package.json` bump (release-only)**; `pnpm build` passes; committed separately (R13)
- [ ] AI-x-SDLC `guides/flow-next.md` backend list + changelog updated; GF `spec/05-cross-model-review.md` verified + `dist/gf.html` re-rendered; vault cross-model-review / Skills Catalog / Release Timeline notes updated (R13)

## Done summary
Walked the full documentation chain for the shipped `cursor` review backend (R13, no version bump). Repo docs: `flowctl.md` (cmd list + new `### cursor` section + review-backend grammar + config-table enum fix), `README.md` (3 backend lists), `GLOSSARY.md`, `CHANGELOG.md` `## Unreleased`, plus `skills.md` / `teams.md` enumeration sweep, the setup `usage.md` template (+ codex-mirror regen + dogfood `.flow/usage.md` parity). Downstream committed in their own repos: flow-next.dev (Cursor row flipped coming→shipped + receipts `mode` + changelog; `pnpm build` green), AI×SDLC (`guides/flow-next.md` + new Cursor section in `code-review-tools-changelog.md`), GrowthFactors (`spec/05` tightened + re-rendered `dist/{gf,shd,shopfully,flooid}.html` + refreshed bundled `code-factory-onboarding.html`), and the Obsidian vault notes (Vocabulary/Skills-Catalog/Lifecycle/Architecture/Release-Timeline). Codex impl-review SHIP (0 findings); full Python suite green (1284 passed).
## Evidence
- Commits: 535c3b99, 36a15b3a, 7e9af30f, c49d5cd7, 44b8d94f
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q  (1284 passed, 2 skipped, 164 subtests), test_dogfood_template_parity.py + test_install_cursor_parity.py (7 passed, 7 subtests), cd ~/work/flow-next.dev && pnpm build (64 pages built, OK), codex impl-review base=4350b124 -> SHIP (0 introduced, 0 pre_existing)
- PRs:
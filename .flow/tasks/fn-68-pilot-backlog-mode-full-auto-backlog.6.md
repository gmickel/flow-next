---
satisfies: [R11]
---

## Description
Full documentation sweep across the four properties + an `## Unreleased` CHANGELOG entry — **NO version bump** (batched-release rule, memory `defer-version-bumps-batch-releases`).
- **repo:** pilot `SKILL.md` (backlog-mode section + the new verdict verbs, core contract stays thin); `docs/ralph.md` (the autonomy story — backlog mode pushes the consent boundary inside-the-loop-on-block); `docs/README.md` (skill index); `docs/flowctl.md` (`ready --all`, `pilot.autonomy`, decision-log subcommand); `GLOSSARY.md` (backlog mode / triage stage / ask stage / question-valve / decision-log); `STRATEGY.md` (autonomy track); `CHANGELOG.md` (`## Unreleased → ### Added`).
- **flow-next.dev:** backlog mode on the pilot page (or a new `skills/pilot-backlog-mode.mdx`) + **BOTH navbars** (`src/lib/site.ts` navGroups AND `astro.config.mjs` sidebar — the repo CLAUDE.md slug-set warning) + `autonomous/overview.mdx` + the changelog `## Unreleased` entry; `pnpm build` green; **NO `FLOW_NEXT_VERSION` bump**.
- **downstream narrative:** AI×SDLC `guides/flow-next.md` (backlog mode in the pipeline/autonomy framing — consent boundary, human-gated merge + spec-authoring, surface-don't-block) + GF microsite autonomy section.

**Size:** L (many files, mechanical) · deps .4
**Files:** repo docs (7), `~/work/flow-next.dev/**`, `~/work/AI-x-SDLC-Starter-Kit/guides/flow-next.md`, `~/work/code-factory-package/**`

## Investigation targets
**Required:**
- `plugins/flow-next/docs/ralph.md` — the autonomy narrative (pilot/land) to extend
- `~/work/flow-next.dev/src/lib/site.ts` + `~/work/flow-next.dev/astro.config.mjs` — the TWO navbars (keep in sync)
- `~/work/AI-x-SDLC-Starter-Kit/guides/flow-next.md` — the pipeline/autonomy framing

## Key context
Both flow-next.dev navbars must change together or the page silently vanishes from the rail (repo CLAUDE.md). NO version bump — stage everything under `## Unreleased`; the batched release decides the number later.

## Acceptance
- [ ] repo docs updated (pilot SKILL.md, ralph.md, README.md, flowctl.md, GLOSSARY.md, STRATEGY.md) + `## Unreleased` CHANGELOG `### Added` entry; **no** version bump.
- [ ] flow-next.dev: backlog mode documented + **BOTH** navbars updated (site.ts navGroups AND astro.config.mjs sidebar) + autonomous/overview + changelog Unreleased; `pnpm build` green; **no** `FLOW_NEXT_VERSION` bump.
- [ ] downstream: AI×SDLC `guides/flow-next.md` + GF microsite autonomy section reflect backlog mode (consent boundary, human-gated merge/authoring, surface-don't-block).

## Done summary
Full documentation sweep for pilot backlog mode (fn-68) across four properties, no version bump (batched-release rule). Repo: ralph.md (autonomy story — consent boundary moves inside-the-loop-on-block), README.md skill index, flowctl.md (ready --all, pilot-log, pilot.autonomy/pilot.gateClasses), GLOSSARY.md (backlog mode / triage stage / ask stage-question valve / decision-log terms + Pilot/Verdict updates), STRATEGY.md autonomy track, and CHANGELOG.md ## Unreleased (full .1/.3/.4/.5 capability + .6 doc-sweep). flow-next.dev: backlog-mode section on the pilot page + autonomous/overview + changelog Unreleased (pnpm build green; both navbars already list Pilot — no navbar edit needed). Downstream: AI×SDLC guides/flow-next.md pipeline/autonomy framing + GF microsite spec/08-autonomy.md (re-stamped overlay provenance + re-rendered all four dist lenses). Pilot SKILL.md backlog wiring was authored in fn-68.4 — this task extended the surrounding docs, no duplication.
## Evidence
- Commits: 9bbd3fd3a1811b32f28034ce4b53fcbc1f125353
- Tests: flowctl ready --all --json (verified facts schema), flowctl pilot-log append/summary --help (verified subcommand), flowctl config get pilot.autonomy/pilot.gateClasses (verified keys), flowctl glossary list --json (38 terms, new entries parse), cd ~/work/flow-next.dev && pnpm build (green, 64 pages, anchors validated), cd ~/work/code-factory-package && bun scripts/render {gf,shd,shopfully,flooid} + --check (self-contained/under-2MB/spec-pure all OK) + bun scripts/test.mjs (27 passed), flowctl triage-skip (SHIP, release-chore docs-only)
- PRs:
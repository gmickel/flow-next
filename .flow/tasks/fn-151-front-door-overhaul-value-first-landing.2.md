---
satisfies: [R16, R17, R18, R19, R20, R39]
---
# fn-151-front-door-overhaul-value-first-landing.2 flow-next.dev supporting pages, proof page, and nav

## Description
Reorder the flow-next.dev supporting pages to the spine, add the new proof page carrying the long-form evidence argument, fix the docs-site count drift, and wire both navigation sources.

**Size:** M
**Files:** `src/content/docs/strategy/why-flow-next.mdx`, `src/content/docs/introduction.mdx`, `src/content/docs/install.mdx`, `src/content/docs/proof/evidence.mdx` (new), `src/content/docs/subagents/overview.mdx`, `src/lib/site.ts`, `astro.config.mjs`

### Approach

**`why-flow-next.mdx`.** Reorder to the spine: the bottleneck moved, then the measured problem, then the answer. This page becomes the canonical long-form home for the SlopCodeBench treatment, so the landing band can stay short and link here. Keep the touch-point collapse table and the autonomy-dial section as they are; both are strong.

**New `proof/evidence.mdx`.** Two parts.

Part one, the measured problem in full: the SlopCodeBench setup and results tables, the quality-prompt finding, the cost-growth figure, and the honest statement of what the paper shows versus what we claim. Cite `https://arxiv.org/html/2603.24755v1`.

Part two, one capsule of roughly 120 words titled plainly, recording the plan-sync skip-gate. Read `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md` in this repository directly rather than reconstructing it. The facts: a deterministic gate to skip the expensive plan-sync agent was designed, built, and fully tested; cross-repo validation replayed 27 real completed-task scenarios from three external repositories against ground truth from the real agent; it produced a genuine false skip where a change altered a downstream task's meaning while touching no file or symbol that task referenced; its skip rate was 1 in 15 against a 50% design threshold; it was removed from the shipped CLI and a decision record written telling us not to try again. State it as facts and stop. No adjective, no self-congratulation, no framing sentence explaining why the story is impressive. The facts carry it; anything added destroys it.

**`introduction.mdx`.** Value before install. Today the page opens with a definition and a diagram, then five harness install blocks, and only reaches "What you get" at line 101. Move the outcome summary above the install blocks. Nothing needs deleting, only reordering. While here, make its harness-tiering sentence at line 144 match the canonical formulation (task 4 owns the canonical statement in `platforms.md`).

**`install.mdx`.** Add three lines at the top: what setup actually does, how long it takes, and how to undo it. `rm -rf .flow/` is one of the best things about this product and it currently appears nowhere near the top of the install page.

**Anchor integrity, and why this is not covered by the build.** Three headings back at least eight inbound links: `## Cursor`, `## xAI Grok Build`, and `## Team / org-wide deployment (Claude Code managed settings)`. Inbound links live in `introduction.mdx:30,89,144`, `first-30-minutes.mdx:10`, `review/workflow.mdx:36`, `orchestration/index.mdx:190`, `skills/setup.mdx:61,72`, `releases/changelog.mdx:1045`, and in the OTHER repository at `README.md:405` and `plugins/flow-next/docs/platforms.md:62`. Starlight does not validate cross-file anchors, and no build in either repository catches the cross-repo case. Preserve the three heading strings exactly. If one must change, update all inbound links in the same change set including the two cross-repo ones.

**Count fix.** `subagents/overview.mdx:8` says "22 subagents". The real count is 21 (`plugins/flow-next/agents/` has 21 files; the page's own breakdown of 9 planning scouts plus 8 readiness scouts plus 3 work-role plus 1 resolver also sums to 21). This is a reference page, not a front door, so the count stays and is corrected rather than removed.

**Navigation, both sources.** Add `proof/evidence` to `src/lib/site.ts` `navGroups` (positional tuple form, Proof group) and to the Starlight `sidebar` in `astro.config.mjs` (object form, Proof group). Editing one and not the other is a recurring bug in this repository and the page silently vanishes from the rail. Verify with the slug-set diff in `CLAUDE.md`; only `install` and `introduction` may differ.

### Investigation targets

**Required:**
- `src/content/docs/proof/field-notes.mdx` - the existing proof-section register to match
- `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md` in the flow-next repo - source for the capsule, read it, do not reconstruct
- `src/lib/site.ts:8-13` - tuple-form nav, Proof group
- `astro.config.mjs:285-291` - object-form sidebar, Proof group
- `src/content/docs/install.mdx:68,102,162` - the three anchor-bearing headings

**Optional:**
- `CLAUDE.md:54-67` - the two-nav-sources rule and its diff check
- `src/content/docs/strategy/verification-spine.mdx` - where lineage citations are confined

### Key context

Lineage citations to Wei, Karpathy, Vogels, Sonar, and Willison are confined to `/strategy/verification-spine/` and must not spread to the new evidence page. SlopCodeBench is outside that restriction.

Copy rules apply to every word: no em dashes, straight quotes only (verbatim third-party quotations keep the author's own punctuation), flat present-tense claims with no hedging, no "not X but Y" construction, and none of the banned phrases listed in task 1.

## Acceptance
- [ ] `why-flow-next.mdx` follows the spine and holds the long-form SlopCodeBench treatment
- [ ] `proof/evidence.mdx` exists with the full measured-problem argument and the plan-sync capsule at roughly 120 words, stated as facts with no self-congratulation
- [ ] The capsule was written from the decision record, not reconstructed from memory
- [ ] `introduction.mdx` presents value before the harness install blocks
- [ ] `install.mdx` opens with what setup does, how long it takes, and how to undo it
- [ ] The three anchor-bearing `install.mdx` headings keep their exact text, or all inbound links including the two cross-repo ones are updated in the same change set
- [ ] `subagents/overview.mdx` says 21 subagents
- [ ] `proof/evidence` is present in BOTH `src/lib/site.ts` navGroups and the `astro.config.mjs` Starlight sidebar
- [ ] The slug-set diff between the two nav sources shows only `install` and `introduction`
- [ ] No lineage citation to Wei, Karpathy, Vogels, Sonar, or Willison appears outside `/strategy/verification-spine/`
- [ ] `pnpm check` and `pnpm build` pass
- [ ] No em dashes, no curly quotes outside verbatim quotations, no banned phrases, no hedging


## Done summary
Reordered `strategy/why-flow-next.mdx` to the spine and gave it the long-form SlopCodeBench treatment, added `proof/evidence.mdx` carrying the measured-problem argument in full plus a 122-word capsule recording the plan-sync skip gate our own eval removed, moved the outcome summary above the harness install blocks in `introduction.mdx`, opened `install.mdx` with what setup does, how long it takes, and how to undo it, corrected the subagent count to 21, and registered the new page in both navigation sources.

The three anchor-bearing `install.mdx` headings are byte-unchanged, verified against the built HTML, so the eight inbound links including the two from the flow-next repo still resolve.

Note for the conductor: the nav slug-set diff prints three astro-only slugs, not the two the acceptance criterion names. `first-30-minutes` is a pre-existing third hardcoded DocsRail top-link (`src/components/DocsRail.astro:30`) that the check description in `CLAUDE.md:61-67` predates. It was present in the pre-edit baseline and this change did not alter the diff by a single line. Fixing it is a one-line edit to the `CLAUDE.md` check description, which is outside this task's file scope and belongs with the global verification pass.
## Evidence
- Commits: flow-next.dev:9fe165ec60fd7fe78c130126ea48459b1ffdddda, flow-next.dev integration merge: 4ebd9d6
- Tests: baseline (pre-edit, a09f91a4): pnpm install --frozen-lockfile && pnpm check && pnpm build -> green, 76 pages built, pnpm check -> green, Result (14 files): 0 errors, 0 warnings, 0 hints, pnpm build -> green, 77 page(s) built (new proof/evidence page), nav slug-set diff (CLAUDE.md check) -> byte-identical to pre-edit baseline (first-30-minutes, install, introduction); proof/evidence absent from the diff, proof/evidence registered in both sources -> grep hit in astro.config.mjs and src/lib/site.ts; rendered rail link and Starlight prev/next both present in dist, anchor integrity -> dist/install/index.html carries id="xai-grok-build", id="cursor", id="team--org-wide-deployment-claude-code-managed-settings"; git diff shows no heading line changed, internal link resolution -> dist/proof/evidence/, dist/strategy/verification-spine/, dist/strategy/pipeline/, dist/proof/field-notes/ all built, em dash + curly quote census on why-flow-next.mdx, introduction.mdx, install.mdx, proof/evidence.mdx -> 0 and 0 (22 em dashes cleared from install.mdx, 6 from introduction.mdx, replaced per sentence), banned-phrase grep over the four owned pages -> no output, lineage citation grep (Wei|Karpathy|Vogels|Sonar|Willison) outside strategy/verification-spine -> no output, PSVI / Velocity Index grep over src/ -> no output, client-name grep (6 patterns, ~/.claude/flow-next-client-names.txt) over src/ -> no output, plan-sync capsule word count -> 122 words, canonical harness-tiering sentence -> byte-identical to the spec R26 string, integrated flow-next.dev target (band + docs merged): pnpm check -> 0 errors/warnings/hints; pnpm build -> 77 pages, exit 0
- PRs:
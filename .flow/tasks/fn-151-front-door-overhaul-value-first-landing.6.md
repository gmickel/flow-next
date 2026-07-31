---
satisfies: [R27, R28, R29, R30, R31, R32, R33, R34, R35, R36]
---
# fn-151-front-door-overhaul-value-first-landing.6 Cross-repo gate, boundary greps, and changelogs

## Description
Final gate across all three repositories: boundary greps, copy-rule sweep over everything the earlier tasks wrote, the docs-site changelog entry, and the visual and build verification that the spec's own criteria depend on.

**Size:** S/M
**Files:** `src/content/docs/releases/changelog.mdx` (flow-next.dev). Otherwise verification and targeted fixes across surfaces the earlier tasks touched.

### Approach

**Boundary greps. Both must produce no output.**

```bash
grep -ri "PSVI\|Velocity Index" ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/
grep -riwf ~/.claude/flow-next-client-names.txt ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/
```

The client-name pattern file is private and deliberately lives outside this repository. If it is missing, report that rather than skipping the gate.

**Testimonial integrity.** Every published quote must resolve to a public URL and ship verbatim, including the author's own punctuation. Re-verify the three URLs resolve. The curly apostrophe in the raydocs quote stays; it is the author's. The excluded X/Twitter set must not have reappeared anywhere.

**Copy-rule sweep** over every file the earlier tasks wrote. Check for: em dashes, curly quotes outside verbatim quotations, hedging qualifiers in front of capabilities that exist ("aims to", "designed to", "can help you", "we believe"), "not X but Y" constructions beyond the two grandfathered lines, and the banned-phrase list from task 1. The one sanctioned exception is the evidence-band close, where precision about what the paper does and does not show is deliberate and must survive.

**Docs-site changelog.** `src/content/docs/releases/changelog.mdx:8-10` has an `## Unreleased` section holding the placeholder "No unreleased changes yet." Replace it. Register is customer-facing and problem-first per `agent_docs/releasing.md`: lead with what was wrong for the reader and what changes now, upgrade actions first and imperative, numbers as outcomes rather than inventory, machinery in the technical tail. Apply the rejection test: hide the technical tail, and if a reader cannot say what became easier or clearer, rewrite it. No version bump, no `FLOW_NEXT_VERSION` change.

**Verification the spec depends on.**

- flow-next.dev: `pnpm check` and `pnpm build`. Then walk the `DESIGN.md` Visual QA Checklist including the mobile, keyboard-focus, and video-poster steps task 2 added. Open search on both the landing and a docs page; search `ralph` for readable results and `gf` for a clean empty state.
- Landing at desktop and mobile widths: no horizontal overflow, keyboard focus visible, no dead viewport between the harness strip and the following section, video band plays or shows its poster.
- Decay plot: confirm it renders complete with JavaScript disabled, and that the draw-on does not run under `prefers-reduced-motion`.
- mickel.tech: `bun run build` and `bun x biome check .`.
- flow-next repo: every relative link in `README.md` resolves. Run the repository's own offline docs linkcheck if reachable locally.
- Nav parity: the slug-set diff between `src/lib/site.ts` and `astro.config.mjs` shows only `install` and `introduction`.

**Cross-repo consistency check.** The six outcome headings must be byte-identical between the landing and the README. The canonical harness-tiering sentence must read the same in `platforms.md`, the README prose, the README platforms table, `introduction.mdx`, and the mickel.tech platforms section. Diff them rather than eyeballing.

**Evidence.** Record all three commit SHAs in the done summary and in the evidence JSON `commits` array, each prefixed with its repository name, since the schema is shaped for one repository.

### Investigation targets

**Required:**
- `agent_docs/testimonials.md` - the boundary gates and the verified quote pool
- `agent_docs/releasing.md` - the docs-site changelog register and format
- `src/content/docs/releases/changelog.mdx:1-12` - the Unreleased placeholder to replace
- `DESIGN.md` Visual QA Checklist - as updated by task 2

**Optional:**
- `.flow/specs/fn-151-front-door-overhaul-value-first-landing.md` - the full R-ID list to check coverage against

### Key context

This task is the only place the three repositories are checked against each other. Earlier tasks each verified their own repository; nothing before this point catches a heading that drifted between the landing and the README, or a tiering sentence that ended up phrased four different ways.

No version bump anywhere. No `FLOW_NEXT_VERSION` change. Changelog entries stay under `## Unreleased` in both the repository and the docs site.

## Acceptance
- [ ] Both boundary greps exit clean; a missing client-name pattern file is reported, not skipped
- [ ] All published testimonial URLs resolve; quotes are verbatim including the author's punctuation; the excluded set has not reappeared
- [ ] Copy-rule sweep is clean across every file the earlier tasks wrote, with the evidence-band close as the one sanctioned exception
- [ ] Docs-site `## Unreleased` placeholder is replaced with a problem-first customer-register entry that passes the hide-the-tail rejection test
- [ ] `pnpm check` and `pnpm build` pass; the DESIGN.md Visual QA Checklist is walked including the new mobile, keyboard-focus, and video-poster steps
- [ ] Search works on both the landing and a docs page; `ralph` returns readable results and `gf` a clean empty state
- [ ] The decay plot renders complete with JavaScript disabled and does not animate under `prefers-reduced-motion`
- [ ] `bun run build` and `bun x biome check .` pass for mickel.tech
- [ ] Every relative link in the README resolves
- [ ] Nav slug-set diff shows only `install` and `introduction`
- [ ] The six outcome headings are byte-identical between the landing and the README
- [ ] The canonical tiering sentence reads identically across platforms.md, README prose, the README table, introduction.mdx, and mickel.tech
- [ ] No version bump and no `FLOW_NEXT_VERSION` change anywhere
- [ ] All three commit SHAs recorded in the done summary and evidence JSON, each prefixed with its repository


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

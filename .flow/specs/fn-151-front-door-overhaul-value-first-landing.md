# fn-151-front-door-overhaul-value-first-landing Front-door overhaul: value-first landing, README, and property alignment

## Goal & Context
<!-- scope: business -->

Marketing is the weakest part of flow-next. The product is field-hardened, evidence-driven, and unusually honest, and none of that reaches a cold visitor in the first thirty seconds.

Both front doors run mechanics-first, proof-last. The flow-next.dev landing puts seventeen competing mechanism-named objects above the fold (nine glyph pillars plus eight feature cards) before it has named a problem the reader has. The README delivers eleven badges, a GIF, then a five-paragraph essay whose strongest paragraph is a two-hundred-word wall of statistics, and it puts every scrap of adoption evidence at line 333 of 500. A visitor who bounces at either surface's halfway mark leaves believing this is an elaborate process tool with no sign that anyone runs it.

Six things a visitor should get immediately and currently does not:

1. Why this exists, framed as a problem they recognise having.
2. That the quality problem is measured rather than asserted, and that the obvious cheap fix has been tested and failed.
3. What they get, stated as outcomes rather than mechanisms.
4. That this runs in real engineering organisations, at breadth, across old and new stacks.
5. That autonomy is a dial they can climb rather than a cliff they jump off.
6. That model and harness routing lets them buy quality where it matters and spend cheaply where it does not.

Every one of those already exists in the material. None is on a front door.

This spec moves proof forward, restates value as outcomes, removes the accumulated incongruencies that undermine credibility, and does it in a way that survives `fn-135 chart` landing without a second overhaul.

Target readers, in priority order: the skeptical staff engineer evaluating in thirty seconds, the team lead deciding whether to pilot it, the head of engineering deciding whether to roll it out.

## Architecture & Data Models
<!-- scope: technical -->

### The narrative spine

One arc, five beats, applied across all three properties in each property's own register. This is the vault's existing claim hierarchy reordered so proof arrives before mechanism.

1. **The turn.** Name the reader's situation, then make the claim. Implementation got cheap; everything downstream did not.
2. **The measured problem.** SlopCodeBench. The intrigue hook, the reason we exist, and the not-vibe-coded signal in one move, and it works because the research is not ours.
3. **What you get, as outcomes.** Six cards. Mechanisms appear as the evidence line beneath each outcome, never as the heading.
4. **Proof of breadth.** Where it already runs, at scale register, plus the honest-asymmetry paragraph, plus the linkable open-source record.
5. **Pick your path.** Solo, team, org, then install.

Register per property, unchanged from the vault tone map: README is a skeptical staff engineer, flow-next.dev is a practitioner and agent-legible, mickel.tech is client and employer credibility.

### The six outcomes (canonical wording, used on both front doors)

1. **Ship more without lowering the bar.** A different model reviews every plan and every implementation, the loop iterates until SHIP, and a task cannot be marked done without evidence JSON.
2. **Reviews stop being where work waits.** The pull request arrives explaining itself: which acceptance criterion each change satisfies, which decisions still need a human, what deliberately did not change.
3. **Your team's context stops living in three people's heads.** Specs, decisions, glossary, and memory are files in your repository that the next run reads.
4. **Climb to autonomy without a leap of faith.** One dial from a supervised pair to a loop draining the backlog overnight. The gates do not change as you climb.
5. **Spend the expensive model where it earns its keep.** Route any model to any role, by parameter or by sentence. Cost and quality become steering decisions.
6. **Your process outlives your agent.** The same specs, gates, receipts, and task state across harnesses. Everything in your repository. Uninstall is `rm -rf .flow/`.

### Landing page composition (flow-next.dev `src/pages/index.astro`)

| Position | Section | Change |
|---|---|---|
| 1 | Hero | Problem line added, nine-pillar grid cut, visual reduced to terminal plus receipt, visual refresh per the licence below |
| 2 | Harness strip | Unchanged |
| 3 | Evidence band | New. Dark full-bleed. SlopCodeBench plus decay plot plus the verify tape relocated here |
| 4 | Outcome cards | Eight feature cards become the six outcomes |
| 5 | Pipeline video and menu recipes | Video kept, menu copy trimmed, task graph and command palette relocated here from the hero |
| 6 | Autonomy dial | Kept, section number dropped |
| 7 | Where it already runs | Promoted from position 8. Breadth, honest asymmetry, adoption strip, quotes |
| 8 | Pick your path | New. Three routes plus one reserved line |
| 9 | Notable updates | Shrunk to lead plus two |
| 10 | Quickstart band | Unchanged |

### Chart-proofing (fn-135 is ready, plan-reviewed, nine tasks, and unblocked: fn-141 has landed)

fn-135 ships `/flow-next:chart` (pre-capture discovery) and `/flow-next:guide` (the router), and its R19 demands a pipeline-level docs change touching nearly every surface this spec edits. Six rules keep this overhaul from needing a second pass:

1. Front doors present the arc (decide, build, prove), not the stage list. Stage names live one click down.
2. Scope claims are written so chart swaps a noun, not a clause. "From the conversation you already had to a merged pull request" becomes "from an idea nobody has shaped yet to a merged pull request".
3. Do not claim complete idea-to-merge coverage yet. Structure copy so turning that claim on is an addition.
4. The path router's fourth line is a reserved slot that becomes `/flow-next:guide`.
5. No command, agent, or skill counts on front doors. Link the catalog instead.
6. Lead prompt-first now, so chart arrives as more evidence for a claim already on the page.

### Hero visual refresh licence

Confined to the hero. Everything below the harness strip is composition against the existing system.

Two materials, offset: the terminal is a screen, the receipt is paper, and the current four-panel grid flattens that difference into a dashboard. Terminal becomes the dark ground plane; the receipt sits over it with the one shadow `DESIGN.md` already reserves for the hero mockup, rotated slightly off-axis. Type scale may grow and tighten on the h1 since it has less competing with it. Three type voices in the first viewport and no more: eyebrow in mono, claim in Fraunces, problem line in IBM Plex Sans. More air above the eyebrow, wider gutter between copy and visual.

Boundary: no new colour tokens, no new typeface, no rail change, nothing that forces a matching change on a docs page. If an idea requires touching `tokens.css`, it is out of scope. The test is that a docs page opened in the next tab still looks like the same site.

### The decay plot (the one new signature device)

Hand-authored SVG on the ink field. Amber curve climbing for agent code-quality erosion across checkpoints; teal flat line for the 48 maintained human repositories. Two annotations only, in IBM Plex Mono: `0.68` and `0.31`. Source label and paper link beneath. No charting library. One scroll-triggered stroke draw-on gated behind `prefers-reduced-motion`. Amber is already the token `DESIGN.md` reserves for adversarial and signal, so this is the palette's intended use.

### Surface map

| Repository | Surfaces |
|---|---|
| `flow-next` | `README.md`, `CHANGELOG.md`, `plugins/flow-next/docs/platforms.md` |
| `flow-next.dev` | `src/pages/index.astro`, `src/styles/home*.css`, a new evidence-band component, `strategy/why-flow-next.mdx`, `introduction.mdx`, new `proof/evidence.mdx`, `install.mdx`, `subagents/overview.mdx`, `releases/changelog.mdx`, `src/lib/site.ts`, `astro.config.mjs`, `DESIGN.md` |
| `mickel.tech` | `app/apps/flow-next/page.tsx`, `lib/apps.ts` |

Each repository commits separately. The flow-next.dev and mickel.tech work happens in their own clean worktrees, and their commit SHAs are reported as evidence against this spec.

### Canonical harness tiering (single formulation, R26)

`plugins/flow-next/docs/platforms.md` is the canonical statement. Every other surface restates it verbatim or links to it:

> First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, and xAI Grok Build. Community port for OpenCode.

Grok Build qualifies on the same standard Cursor already meets: its own setup detection signal (`GROK_AGENT=1`, fn-126), canonical plugin files consumed as-is, slash commands, and verified multi-agent flows. Ralph is intentionally not built for either. Because every surface restates one sentence from one canonical home, demoting Grok later is a one-place edit.

### Contradiction resolutions (from the fn-151 gap pass)

- **R13 versus R25.** R13 governs front-door prose: the landing, the README narrative, and the mickel.tech page carry no counts. R25 governs reference documents, where an accurate count earns its place: `platforms.md`, `subagents/overview.mdx`, `docs/skills.md`, and the README's demoted reference tail keep counts and are corrected to 21 agents. A count is banned where it sells and kept where it informs.
- **Canonical wording versus per-property register.** The six outcome *headings* ship word-for-word identically on the landing and in the README. The supporting body copy adapts to each property's register. Consistency where the claim lives, register where the voice lives.
- **Front-door scope.** Three surfaces: the landing, the README, the mickel.tech page. R13, R14, and R15 bind all three. mickel.tech's own count claims are inside R25's ledger.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Concurrent agents.** Other agents are active in `~/work/flow-next` (fn-137 in the main checkout, fn-135 and fn-148 in other worktrees) and pushing to main. All work for this spec happens in its own worktree; rebase before pushing; never touch another agent's uncommitted files.
- **Lineage citation boundary.** Wei, Karpathy, Vogels, Sonar, and Willison citations remain confined to `/strategy/verification-spine/`. SlopCodeBench is outside that restriction and already ships in the README.
- **Testimonial boundary.** Every published quote resolves to a public URL and ships verbatim including the author's own punctuation. The curly apostrophe in the `raydocs` quote stays. The excluded X/Twitter set must not return.
- **No client names.** Sector descriptors only. No private-vocabulary or private-vocabulary vocabulary anywhere public.
- **No process or speed self-praise.** Release cadence and issue-closure rate are true and banned.
- **The video goes stale on chart.** `pipeline-hero.mp4` animates a route that fn-135 invalidates. Its re-cut is already scoped into fn-135 task 8 and is explicitly out of scope here.
- **fn-135 is unblocked and workable today** (fn-141 landed). No dependency edge is recorded in either direction, because a real edge would block fn-135 needlessly. Instead: **fn-151 should land first.** fn-135 task 7 owns `README.md` and task 8 owns `index.astro`, `site.ts`, `astro.config.mjs`, and `introduction.mdx`; if fn-135 lands first, fn-151's from-scratch recomposition of those files would steamroll it and force exactly the second overhaul this spec exists to avoid. Landing fn-151 first leaves fn-135 four small additions: two nav entries, one routing paragraph, one figcaption string, one README mention.
- **fn-142** (maintainability axis) also inserts a sentence into `README.md`. Whichever lands second preserves the other's claim. R21's "retains every existing section" does not protect a single inserted sentence.
- **Cross-repo anchor fragility.** Three `install.mdx` headings back at least eight inbound links, two of them from the other repository (`README.md` and `platforms.md`). Starlight does not validate cross-file anchors and no build in any repo catches the cross-repo case. Heading text is preserved rather than trusted to a link checker.
- **No precedent for the decay plot.** The flow-next.dev codebase contains no hand-authored chart SVG and no `IntersectionObserver`. Both existing animations are load-triggered with a `prefers-reduced-motion` opt-out; that gating pattern is reusable, the scroll trigger is new.
- **The banned-phrase lists are vault-resident** and unavailable to any delegated implementer. The rules that matter are therefore inlined into task acceptance rather than referenced.
- **Docs-only.** No plugin version bump. Changelog entries land under `## Unreleased`.
- **Em-dash replacement is per sentence.** A global substitution reads worse than the original and will need redoing.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The landing hero states the problem before the claim, in a line set in IBM Plex Sans below the Fraunces claim, and the nine-pillar glyph grid is removed.
- **R2:** The landing hero visual contains the spec header, the terminal transcript, and the receipt only. The task graph and command palette are relocated to the pipeline section.
- **R3:** The hero visual refresh treats terminal and receipt as two distinct materials with the single sanctioned shadow, introduces no new colour token or typeface, changes no rail styling, and leaves `tokens.css` untouched.
- **R4:** A new evidence band sits at landing position 3, presenting the SlopCodeBench setup, result, failed-prompt-fix finding, and a close that states what Flow-Next is without claiming the paper validates it.
- **R5:** The evidence band carries a hand-authored SVG decay plot with two curves, exactly two numeric annotations, a source label, a link to the paper, no charting dependency, and a text alternative describing both trends.
- **R6:** The decay plot's animation is gated behind `prefers-reduced-motion`, and the landing has no motion beyond that plot and the existing pipeline video.
- **R7:** The existing verify tape is relocated into the evidence band as the answer to its argument, and no longer appears as a standalone numbered section.
- **R8:** The landing presents exactly six outcome cards using the canonical wording, with mechanisms appearing only as the evidence line beneath each outcome.
- **R9:** The `01 / 02 / 03 / 04` section numbering is removed from the landing.
- **R10:** The breadth band is promoted above the notable-updates section and contains the enterprise breadth paragraph, the honest-asymmetry paragraph unsoftened, a quiet linked adoption strip, and the three verified quotes as supporting capsules rather than the headline.
- **R11:** The adoption strip carries linked counts and open-source proof, and no count appears in the hero.
- **R12:** A path-router section offers solo, team, and organisation routes plus one reserved line that becomes the `guide` router when fn-135 lands.
- **R13:** No front-door surface quotes a command, agent, subagent, or skill count. Each such claim is replaced by a link to the generated catalog.
- **R14:** Front-door scope claims are phrased so that fn-135 changes a noun rather than a clause, and no front door claims complete idea-to-merge coverage.
- **R15:** Natural-language invocation is stated as a first-class capability on both front doors.
- **R16:** `strategy/why-flow-next.mdx` is reordered to the spine and holds the long-form SlopCodeBench treatment.
- **R17:** A new `proof/evidence.mdx` page exists, carrying the measured-problem argument in full plus one capsule of roughly 120 words recording the plan-sync skip-gate that its own eval killed, stated as facts with no self-congratulation.
- **R18:** `introduction.mdx` presents value before install; the harness install blocks follow the outcome summary.
- **R19:** `install.mdx` opens with what setup does, how long it takes, and how to undo it.
- **R20:** Any page added or renamed appears in both `src/lib/site.ts` `navGroups` and the Starlight `sidebar` in `astro.config.mjs`, and the slug-set diff check produces only `install` and `introduction`.
- **R21:** `README.md` follows the same spine, lands at roughly 360 lines, retains every existing section, and demotes the command inventory out of the main narrative.
- **R22:** The README's adoption and breadth evidence appears within the first quarter of the document.
- **R23:** The README's SlopCodeBench material is scannable rather than a single dense paragraph.
- **R24:** `mickel.tech` reports version 3.9.0, its problem list is stated as reader-recognisable pain rather than mechanism names, its platform statuses match the repository, and it carries the breadth and honest-asymmetry paragraphs.
- **R25:** Every row of the incongruency ledger is resolved: the 22-agents claim in `README.md` and `plugins/flow-next/docs/platforms.md`, the 22-subagents claim on the docs site, the conflicting recipe counts, the stale mickel.tech version, and the three-way harness-tiering contradiction across `README.md` prose, the README platforms table, and `introduction.mdx`.
- **R26:** Harness tiering is stated identically on every surface that states it.
- **R27:** Em dashes are removed from `README.md`, `index.astro`, `introduction.mdx`, `strategy/why-flow-next.mdx`, and `install.mdx`, with replacements chosen per sentence.
- **R28:** Curly quotes are replaced with straight quotes except inside verbatim third-party quotations.
- **R29:** New and rewritten copy states claims flat and in the present tense, with no hedging qualifier in front of a capability that exists. The sole exception is the evidence-band close.
- **R30:** New and rewritten copy contains no negative-parallelism construction beyond the two grandfathered coined lines, and no phrase from the banned-opener, dead-transition, engagement-bait, or tech-marketing lists.
- **R31:** The private-vocabulary vocabulary grep and the private client-name grep both exit clean against every edited surface.
- **R32:** `pnpm build` and `pnpm check` pass in the flow-next.dev worktree, and the DESIGN.md visual QA checklist is walked including search on both a landing and a docs surface.
- **R33:** The landing renders without a dead viewport between the harness strip and the following section, and the pipeline video band either plays or is replaced by its poster.
- **R34:** The landing and README are verified at desktop and mobile widths, with no horizontal overflow and visible keyboard focus retained.
- **R35:** No plugin version bump occurs. Changelog additions land under `## Unreleased` in both the repository and the docs site.
- **R36:** Each repository is committed separately. The flow-next.dev and mickel.tech commit SHAs are recorded in the task done-summary and in the evidence JSON `commits` array, each prefixed with its repository name so a single-repo schema still carries all three.
- **R37:** `flow-next.dev/DESIGN.md` is updated so its Homepage structure list, Homepage Product Mockup section, and Feature Cards section describe the shipped page rather than the retired one, and its Visual QA Checklist gains the mobile-width, keyboard-focus, and video-poster steps that R32 relies on to verify R33 and R34.
- **R38:** The landing's `siteTitle`, `siteDescription`, and Open Graph and Twitter metadata, and the mickel.tech `lib/apps.ts` tagline and description, are restated in the outcome-first register rather than the mechanism list they currently repeat. If `public/og-image.png` is left showing the retired hero, that is stated as a deliberate deferral rather than left unnoticed.
- **R39:** The three `install.mdx` headings that back inbound anchors keep their exact text, or every inbound link is updated in the same change set, including the two cross-repo links from `README.md` and `plugins/flow-next/docs/platforms.md`.
- **R40:** A `## Unreleased` heading is created in the repository `CHANGELOG.md` above the 3.9.0 entry, matching that file's existing keep-a-changelog subsection style, and the docs-site changelog placeholder is replaced with an entry in the customer-facing problem-first register.
- **R41:** The other two repositories are gated too: `bun run build` and `bun x biome check .` pass for mickel.tech, and the README renders with no broken relative link. Results are recorded as evidence.
- **R42:** The six outcome headings appear word-for-word identically on the landing and in the README; supporting body copy adapts per property register.
- **R43:** The decay plot's resting state is fully drawn. The draw-on animation is an enhancement applied only when the element can be observed entering the viewport, so a deep-link, a restored scroll position, or a missing observer yields a complete chart rather than an empty one.
- **R44:** Front doors describe the pipeline as an arc rather than a stage list, and no front door presents a stage enumeration that fn-135 would invalidate.

## Boundaries
<!-- scope: business -->

Not in this spec:

- **No visual re-skin.** Palette, typefaces, rail, and the ink-and-paper alternation are fixed. The refresh licence stops at the hero.
- **No documentation restructure.** Skills pages, flowctl reference, tasks, review, teams, and autonomous sections keep their current shape and content.
- **No chart or guide documentation.** fn-135 owns every chart-related page, nav entry, and the pipeline video re-cut. This spec only leaves slots.
- **No pipeline video re-cut.** Already scoped into fn-135 task 8.
- **No long-tail em-dash sweep.** The remaining docs files beyond the five front-door surfaces are a separate mechanical pass.
- **No new testimonials.** The verified pool is the pool.
- **No version bump, no release.**
- **No competitor comparison table.** Capability claims on our own terms.
- **No AI x SDLC guide or vault edits.** The downstream walk is separate work.

## Decision Context

**SlopCodeBench gets the full band plus the decay plot, at landing position 3.** It is external, peer-reviewed, not ours, and it directly refutes the cheapest alternative to the whole pipeline. Alternatives considered: a compact stat band with no plot, placing it after the outcome cards, or leaving it in the README only. Chosen because it is the strongest available intrigue hook and because a reader who accepts its argument has already accepted the product's premise.

**The evidence band close states what we are, and stops short of claiming the paper validates us.** The paper names structural discipline enforced through tooling as the untested fix; that is a description of Flow-Next. Saying more would be an overclaim a skeptical reader checks and catches, and losing the band. Everywhere else, copy is flat and unhedged.

**Adoption counts go in the breadth band, never the hero.** A stat row under the hero is the template move and reads as try-hard on a tool this technical. Beside the enterprise breadth paragraph the same numbers read as fact.

**The eval-that-said-no capsule ships on `/proof/evidence`, not the landing.** It is the only artifact proving the verification claim applies to us rather than only to pipeline output. It stays off the landing because a cold reader wants adoption evidence there, not a self-referential story. The 2026-07-20 register rule bans process and speed self-praise; this is a quality-mechanism claim, not a turnaround brag, and the maintainer's own story-beat guidance names this exact story as the register example.

**The honest-asymmetry paragraph is promoted unsoftened.** Naming a real adoption cost and then closing it is a confidence move, and it pre-empts the objection a skeptical senior engineer is already forming. Softening the friction line was considered and rejected: it removes the only thing that makes the paragraph work.

**Counts leave the front doors permanently.** They have drifted twice, they move again when fn-135 lands, and a marketing surface quoting an inventory number is a maintenance liability with no reader benefit. Generated catalogs keep exact numbers.

**The overhaul is chart-proofed rather than deferred until after fn-135.** fn-135 is blocked on fn-141 and carries nine tasks; the front doors are damaging credibility now. Building against the arc rather than the stage list means fn-135's docs task inherits slots instead of a rewrite.

## Quick commands

```bash
# flow-next.dev (per-task, in its own worktree)
cd ~/work/flow-next.dev && pnpm check && pnpm build

# mickel.tech
cd ~/work/mickel.tech && bun run build && bun x biome check .

# nav parity (flow-next.dev) - only install + introduction may differ
diff <(grep -oE 'slug: "[^"]+"' astro.config.mjs | sed -E 's/slug: "([^"]+)"/\1/' | sort -u) \
     <(grep -oE '"[a-z][a-zA-Z0-9/_-]*"' src/lib/site.ts | tr -d '"' | sort -u)

# boundary gates - both MUST produce no output
grep -ri "private-vocabulary\|private-vocabulary" ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/
grep -riwf <private client-names list> ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/

# em-dash census on the five front-door surfaces
grep -c '—' README.md ~/work/flow-next.dev/src/pages/index.astro
```

## Strategy Alignment

Active tracks served by this plan:

- **Spec-driven team patterns** - the front doors are where the methodology identity is either legible or invisible. Promoting the breadth evidence, the honest asymmetry, and the outcome framing is what makes the methodology claim land on a cold visitor instead of reading as an elaborate tool.
- **Cross-platform parity** - R26 resolves a three-way contradiction about which harnesses are first-class, and establishes one canonical sentence with a single home, so the claim stops drifting per surface.

## Early proof point

Task 1 validates the core approach: the evidence band with its decay plot is the one genuinely new thing here, it has no precedent in the codebase (no hand-authored chart SVG, no IntersectionObserver), and it carries the beat the whole recomposition is built around. If the plot cannot be made to read in three seconds inside the existing palette, or the drawn-by-default requirement makes the animation pointless, reconsider the compact-stat-band variant before task 5 recomposes the page around it.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1-R3 | Hero problem line, reduced visual, refresh boundary | .5 | - |
| R4-R6 | Evidence band, decay plot, motion gating | .1 | - |
| R7-R12 | Verify-tape relocation, six outcomes, numbering, breadth band, adoption strip, path router | .5 | - |
| R13-R15 | Counts off front doors, noun-swap scope claims, prompt-first | .3, .4 | .3 owns README and canonical prose; .4 owns mickel.tech |
| R16-R20 | Supporting pages, proof page, install opener, nav both sources | .2 | - |
| R21-R23 | README recomposition, evidence position, scannable SlopCodeBench | .3 | - |
| R24-R26 | mickel.tech alignment, ledger, canonical tiering | .3, .4 | .4 writes the canonical sentence; .3 restates it |
| R27-R31 | Em dashes, curly quotes, confidence register, banned phrases, boundary greps | .6 | Applied inline by every task, verified globally in .6 |
| R32-R36 | Build gates, live-render checks, responsive and a11y, no bump, per-repo evidence | .6 | - |
| R37 | DESIGN.md sync and QA-checklist extension | .5 | Written by the task that ships the page it describes |
| R38 | Metadata and registry copy in outcome register | .5, .4 | .5 owns site metadata; .4 owns lib/apps.ts |
| R39 | install.mdx anchor integrity incl. cross-repo links | .2 | - |
| R40 | Repo CHANGELOG Unreleased + docs-site entry | .3, .6 | .3 opens the repo section; .6 writes the docs-site entry |
| R41 | mickel.tech and README gates | .4, .6 | - |
| R42 | Outcome headings byte-identical across front doors | .3, .6 | .3 authors; .6 diffs |
| R43 | Decay plot drawn by default | .1 | - |
| R44 | Arc not stage list | .5 | - |

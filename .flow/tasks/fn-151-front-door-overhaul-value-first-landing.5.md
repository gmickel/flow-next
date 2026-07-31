---
satisfies: [R1, R2, R3, R7, R8, R9, R10, R11, R12, R37, R38, R44]
---
# fn-151-front-door-overhaul-value-first-landing.5 Landing recomposition, hero refresh, and DESIGN.md

## Description
Recompose the landing page: new hero with the problem line and the refreshed visual, six outcome cards replacing seventeen mechanism-named objects, the breadth band promoted, a new path router, section numbering removed, and the evidence band from task 1 mounted at position 3.

**Size:** M/L (single-file-dominant, cohesive; do not split further)
**Files:** `src/pages/index.astro`, `src/styles/home.css`, `src/styles/home-cards.css`, `src/styles/home-product.css`, `src/styles/home-proof.css`, `src/styles/home-autonomy.css`, `DESIGN.md`

### Approach

**Final section order:** hero, harness strip, evidence band, outcome cards, pipeline video and menu recipes, autonomy dial, where it already runs, pick your path, notable updates, quickstart.

**Hero.** Keep the eyebrow and the Fraunces claim. Add below it, in IBM Plex Sans, sized between h1 and body, weight 700, full-strength on ink:

> Implementation got cheap. Reviewing it, verifying it, and keeping a codebase coherent did not.

Then the claim paragraph, tightened to three lines with two links (receipts, loop) instead of four. Delete the `proofPillars` array and its `.proof-row` markup entirely.

**Hero visual refresh.** Today `.product` is a four-panel grid. Remove the `.graph` (task graph) and `.palette` (command palette) panels and relocate them into the pipeline section. What remains is the spec header strip, the terminal transcript, and the receipt, recomposed as two materials rather than equal grid cells: the terminal as the dark ground plane, the receipt offset over it with the single `--shadow` that DESIGN.md reserves for the hero mockup, rotated slightly off-axis. The h1 may grow and tighten now that less competes with it. Three type voices in the first viewport and no more: eyebrow in mono, claim in Fraunces, problem line in Plex Sans. More air above the eyebrow, wider gutter between copy column and visual.

Hard boundary: no new colour token, no new typeface, no rail change, no edit to `tokens.css`. The test is that a docs page opened in the next tab still looks like the same site.

**Six outcome cards.** Replace the eight-entry `featureCards` array with six. Headings ship word-for-word as written in the spec's Architecture section and must match the README exactly. Mechanisms appear only in the evidence line beneath each outcome, never in a heading.

**Mount the evidence band** from task 1 at position 3 and delete the standalone `.verify` section whose tape now lives inside it.

**Section numbering.** Remove the `01 /`, `02 /`, `03 /`, `04 /` eyebrow strings at `index.astro:439`, `456`, `482`, `544`. They are inline literals, not data-driven. Keep the kicker labels themselves.

**Where it already runs.** Promote above notable-updates. Order: breadth paragraph (worldwide enterprise engineering organisations, CAD and construction software, proptech, education; modern monorepos and hundred-repo microservice estates alongside thirty-year-old legacy stacks; GitHub Enterprise, GitLab, Jira; Windows included because the field runs Windows), then the discovery-throughput sentence (a two to three hour structured discovery interview reliably produces eight to eleven implementation-ready specs; product and engineering leads report a clear efficiency gain and edge cases caught during spec review), then the honest-asymmetry paragraph verbatim and unsoftened from `src/content/docs/proof/field-notes.mdx:20`, then a quiet linked adoption strip, then the three verified quotes as supporting capsules.

Adoption strip contents: 669 stars, 52 forks, 8 contributors (all linked to GitHub), CI on Linux, macOS and Windows every push, featured in awesome-claude-code-workflows, external contributors shipping flowctl patches. Mono-set, quiet, factual. No counts in the hero. Re-verify the three numbers with `gh api repos/gmickel/flow-next` before shipping.

**Pick your path.** Three cards on the receipt-stub motif using `RecipeCard` or a sibling: solo today to `/first-30-minutes/`; a team adopting it to `/teams/collaboration/`; an organisation rolling it out to `/install/#team--org-wide-deployment-claude-code-managed-settings`. Below them one line reading "Not sure which applies? Start at [When to use](/strategy/when-to-use/)." That line is a reserved slot; it becomes the `/flow-next:guide` router when fn-135 lands, so keep it a single self-contained string.

**Notable updates** shrinks from lead plus three to lead plus two.

**Metadata.** Restate `siteTitle`, `siteDescription`, and the Open Graph and Twitter description in the outcome-first register. They currently repeat the mechanism list this overhaul removes from visible copy. If `public/og-image.png` still shows the retired hero, say so explicitly in the done summary as a deliberate deferral rather than leaving it unnoticed.

**DESIGN.md.** Update the Homepage structure list, the Homepage Product Mockup section, and the Feature Cards section so they describe what shipped. Add mobile-width, keyboard-focus, and video-poster steps to the Visual QA Checklist, which is currently desktop-only and therefore cannot verify this spec's own responsive and accessibility criteria.

**Arc, not stage list.** Where the page describes the pipeline, describe the movement (decide what to build, build it, prove it shipped) rather than enumerating named stages. Stage names belong one click down. This is what keeps fn-135 from forcing a second overhaul.

### Investigation targets

**Required:**
- `src/pages/index.astro:19-178` - the data arrays being replaced
- `src/pages/index.astro:262-379` - hero and product mockup markup
- `src/content/docs/proof/field-notes.mdx:14-20` - the breadth and honest-asymmetry source paragraphs
- `src/styles/home-product.css:170-276` - the `.paper-receipt` motif and its stamp
- `DESIGN.md:115-160,238-272,360-375` - shape and shadow rules, mockup rules, feature-card rules, QA checklist

**Optional:**
- `src/components/RecipeCard.astro` - props and copy-button script for the path router
- `src/styles/home-proof.css:174-192` - the existing field-line override, order-sensitive

### Design context

`DESIGN.md` governs and is itself updated by this task. Load-bearing rules: 6-8px radius, no oversized pill cards, no nested cards, shadow only for the hero mockup, teal is the primary accent, amber only for adversarial and signal, green reserved for SHIP and completion, no purple and no generic SaaS gradients, status never carried by colour alone. Responsive: desktop rail 220px, homepage rail static below 900px, no horizontal overflow at any width.

### Key context

`home-proof.css:174-175` carries an explicit specificity-override comment. CSS across `home.css`, `home-cards.css`, and `home-proof.css` shares class names and is order-sensitive; check the cascade after removing sections rather than assuming deletion is safe.

Copy rules apply to every word: no em dashes, straight quotes only, flat present-tense claims with no hedging, no "not X but Y" construction, and none of the banned phrases listed in task 1. Two grandfathered exceptions already in the codebase may stay: "ship like engineers, not slot machines" and "the pipeline is a menu, not a rail". Do not introduce a third.

## Acceptance
- [ ] Hero states the problem before the claim, in Plex Sans below the Fraunces claim; `proofPillars` and `.proof-row` are gone
- [ ] Hero visual contains spec header, terminal, and receipt only; task graph and command palette are relocated to the pipeline section
- [ ] Receipt is offset over the terminal with the single sanctioned shadow; no new token, no new typeface, `tokens.css` untouched
- [ ] A docs page opened in the next tab still reads as the same site
- [ ] Evidence band is mounted at position 3 and the standalone `.verify` section is removed
- [ ] Exactly six outcome cards, headings word-for-word identical to the README's
- [ ] `01 /`, `02 /`, `03 /`, `04 /` eyebrow numbers are gone; kicker labels remain
- [ ] Breadth band sits above notable updates and carries the breadth paragraph, the discovery-throughput sentence, the honest-asymmetry paragraph unsoftened, the adoption strip, and the three verified quotes as capsules
- [ ] Adoption counts appear only in the breadth strip, never in the hero, and were re-verified against the GitHub API before shipping
- [ ] Path router ships three routes plus the single-string reserved line
- [ ] Notable updates shows lead plus two
- [ ] Site title, description, and Open Graph and Twitter metadata are outcome-first; og-image staleness is either fixed or explicitly recorded
- [ ] No front-door surface enumerates pipeline stages in a way fn-135 would invalidate
- [ ] `DESIGN.md` homepage structure, product mockup, and feature-card sections describe the shipped page, and the QA checklist gained mobile, keyboard-focus, and video-poster steps
- [ ] No dead viewport between the harness strip and the following section; the video band plays or shows its poster
- [ ] Verified at desktop and mobile widths: no horizontal overflow, keyboard focus visible
- [ ] `pnpm check` and `pnpm build` pass
- [ ] No em dashes, no curly quotes, no banned phrases, no hedging, no new "not X but Y" construction


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

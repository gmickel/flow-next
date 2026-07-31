---
satisfies: [R4, R5, R6, R43]
---
# fn-151-front-door-overhaul-value-first-landing.1 Evidence band component and decay plot

## Description
Build the evidence band as a self-contained Astro component plus its styles, including the decay plot. It is the landing page's new position-3 section and the one new signature device in the whole overhaul. Nothing mounts it yet; task 2 does that.

**Size:** M
**Files:** `src/components/EvidenceBand.astro` (new), `src/styles/home-evidence.css` (new). Do not edit `src/pages/index.astro` in this task.

### Approach

Dark full-bleed band on the ink field, matching the existing `.verify` and `.autonomy` band treatment. Copy is fixed by the spec, reproduce it faithfully:

Heading: **What happens on the twentieth change**

Four paragraphs: the SlopCodeBench setup (11 models, 93 checkpoints, specs fixing only external behaviour); the result (no model finished a problem end to end, best strict pass rate 17.2% falling to 0.5%, structural erosion up in 80% of runs and verbosity in 89.8%, gap against 48 maintained human repositories widening every iteration while human numbers stayed flat); the failed cheap fix (quality-aware prompts cut initial verbosity by about a third, changed the rate of decay not at all, moved no pass-rate subtype, cost up to 48% more, so better instructions do not survive iteration); the close (the authors name structural discipline enforced across checkpoints through tooling as untested, and that is a description of Flow-Next: gates the agent cannot skip, a different model reviewing every handover, a receipt for every claim of done).

Two links out: the paper at `https://arxiv.org/html/2603.24755v1`, and `/strategy/verification-spine/` labelled "how we do it".

Below the prose, render the verify tape currently living in the `.verify` section of `index.astro` (in-loop, impl-review, flowctl done, qa, land, make-pr) as the direct answer to the argument above it. Copy the markup and the `.verify-tape` styling across; task 2 deletes the original.

**The decay plot.** Hand-authored inline SVG, no library, no dependency:
- Amber curve (`--amber`) climbing left to right: agent code-quality erosion across checkpoints.
- Teal line (`--teal`) flat: the 48 maintained human repositories.
- Exactly two annotations, in `--font-mono`: `0.68` on the agent curve, `0.31` on the human line. No legend, no gridlines, no axis ticks. If it needs a legend it has failed.
- Source label and paper link beneath the plot.
- `role="img"` with an `aria-label` describing both trends in words, since the plot carries an argument.

**Animation, and the failure mode that matters.** The resting state is fully drawn (`stroke-dashoffset: 0`). The draw-on is an enhancement layered on top: script sets the undrawn state and animates only when an `IntersectionObserver` is available and reports entry. A visitor arriving by deep link, with a restored scroll position, in a browser without the observer, or with JavaScript off must see a complete chart. Never ship a default state that depends on an event to become correct.

Gate the animation behind `@media (prefers-reduced-motion: reduce)` using the same pattern as `src/styles/home-product.css:278-291`.

### Investigation targets

**Required:**
- `src/styles/tokens.css` - exact token names and values; do not add any new token
- `src/styles/home-proof.css:21-115` - the `.verify` band and `.verify-tape` styling to carry over
- `src/pages/index.astro:437-452` - the verify tape markup being relocated
- `src/styles/home-product.css:278-291` - the reduced-motion gating pattern to copy
- `src/components/ReceiptCallout.astro` - the closest existing receipt-motif component, for texture and dotted-leader treatment

**Optional:**
- `src/styles/home-autonomy.css:193-216` - the other staggered-reveal keyframe, also reduced-motion gated
- `DESIGN.md` - band treatment, amber reserved for adversarial and signal

### Design context

`DESIGN.md` governs. Relevant constraints:
- Amber (`--amber #d99a19`) is the token reserved for adversarial review, signal, and secondary emphasis. The climbing agent curve is exactly that use. Teal (`--teal #1fd5cd`) is the primary accent, correct for the human baseline.
- Deep ink and warm paper are the dominant surfaces; this band is ink.
- Square-ish corners, 6-8px radius, hairline borders that are visible but quiet.
- Shadow only for major overlays or the hero mockup. This band gets none.
- No purple, no generic gradients, no decorative blobs.

### Key context

There is no existing hand-authored chart SVG anywhere in this codebase and no `IntersectionObserver` in `src/`. Both patterns are new here, so there is nothing to copy for the trigger mechanism, only for the reduced-motion gating.

Copy rules apply to every word written in this task: no em dashes, straight quotes only, claims stated flat and present-tense with no hedging qualifier, no "not X but Y" construction, and none of these phrases: "in today's", "it's worth noting", "delve", "dive into", "leverage", "harness", "landscape", "realm", "robust", "game-changer", "cutting-edge", "furthermore", "moreover", "additionally", "supercharge", "unlock", "future-proof". The evidence-band close is the one place precision about what the paper does and does not show is deliberate; that is not hedging and must survive review.

## Acceptance
- [ ] `src/components/EvidenceBand.astro` exists and renders heading, four paragraphs, both outbound links, the decay plot, and the relocated verify tape
- [ ] The close states what Flow-Next is without claiming the paper validates it
- [ ] The decay plot is hand-authored inline SVG with no charting dependency, two curves, exactly two numeric annotations, no legend and no gridlines
- [ ] The plot carries `role="img"` and an `aria-label` describing both trends
- [ ] The plot's resting state is fully drawn; disabling JavaScript or blocking the observer still yields a complete chart
- [ ] The draw-on animation runs only when the element is observed entering the viewport, and is disabled under `prefers-reduced-motion`
- [ ] Only existing tokens from `tokens.css` are used; no new token, no new typeface
- [ ] `src/pages/index.astro` is untouched by this task
- [ ] `pnpm check` and `pnpm build` pass
- [ ] No em dashes, no curly quotes, no banned phrases, no hedging qualifiers in new copy


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

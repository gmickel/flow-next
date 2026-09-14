# fn-142 Maintainability questions at design time, and an honest claim

**Rewritten 2026-09-14.** The July draft predates the direct route, fn-174's overengineering discipline in plan review, and criteria G1/G3. This version keeps the two moves (ask structural questions before code exists; state what the pipeline does not prove) and cuts everything that could push a reviewer toward speculative abstraction. R-IDs keep their July numbers; withdrawn ones are marked, never renumbered. fn-159 has shipped, so the ordering constraint is satisfied.

## Goal & Context
<!-- scope: business -->

The pipeline proves a change does what was asked. No stage asks whether the codebase stayed as changeable as it was, and tests cannot see that. SlopCodeBench (Orlanski et al., Mar 2026) measured the decay when agents extend their own prior code and showed the obvious fix fails: quality prompts to the implementer move the starting point, not the slope, at higher cost. The one cheap place to reason about structure is before code exists.

Since 5.0 that place is two mouths, not one. Plan review is optional on the direct route, so a section that lives only there is skipped on most no-plan specs. The technical refine pass is where a human answers design questions before build. Both get the same questions; neither gets a new spec section, a metric, or a gate.

Move two is honesty, and it is independent of move one: until measurement lands (fn-143), the public claim needs its scope attached. The pipeline proves the change does what was asked and records what it did; it does not prove the codebase stays maintainable. That sentence is true today and reads as confidence, not weakness.

## Architecture & Data Models
<!-- scope: technical -->

Prose only, two surfaces plus copy.

**Plan review.** The review criteria gain one item, Maintainability, with two questions the reviewer answers from the plan as written or marks "none identified":

1. **Duplication** - does this plan already make the same edit, or the same decision, in more than one place?
2. **Structure** - does the plan add a back-edge against the intended dependency direction, or add branching to a function that is already the hottest in its module?

Both are observable in the plan. The July draft's first question ("what plausible future requirement makes this edit happen in more than one place") is dropped: it asks the reviewer to speculate about futures, which is what fn-174's criterion 6 forbids, and answering it tends to prescribe an abstraction against a requirement nobody stated. "Could be cleaner" is out of scope for the section, and the section never recommends adding an abstraction; it names duplication or a structural fact and stops.

The verdict artifact carries the block; the skill writes a one-line pointer into the spec's existing Decision Context. No new canonical section.

**Refine, technical pass.** The same two questions join the technical pass's question set, asked once, answers written into Decision Context by the existing write-back. This is what covers the direct route.

**Blocking calibration.** A maintainability finding alone is advisory. It contributes to NEEDS_WORK only when it names concrete duplication already in the plan, a named back-edge, or a named function absorbing the new branching.

**Copy.** One sentence, byte-identical: "The pipeline proves the change does what was asked and records what it did; it does not prove the codebase stays maintainable." Surfaces: the verification-spine page and FAQ on flow-next.dev, the repo README, the docs home, and the vault Messaging Library.

## API Contracts
<!-- scope: technical -->

Verdict block, advisory:

```
maintainability:
  duplication: <concrete edit or decision made in >1 place in this plan> | none identified
  structure: <named back-edge or named hot function> | none identified
```

Pinned-prompt blast radius: the plan-review prompt is mirrored as a fallback constant in flowctl and hash-pinned; the edit updates the constant, both pins, and the parity fixtures in the same commit, as fn-174 did.

## Edge Cases & Constraints
<!-- scope: technical -->

- G1 applies: the added prose must earn its always-loaded cost; keep the item to the two questions and the calibration rule.
- No numbers, thresholds, scores, or pass/fail on structure; measurement is fn-143's, and advisory even there.
- No copy may claim the pipeline prevents, stops, or fixes decay.
- Works on every review backend; no host-specific formatting.
- Older verdicts without the block stay valid; absence reads as "not asked", never "no risk".

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The plan-review criteria carry a Maintainability item with the two questions, each answered concretely or "none identified". Errors: none beyond the prompt-pin parity tests.
- **R2:** The section records concrete duplication or structural facts only; "could be cleaner" and any recommendation to add an abstraction are documented as out of scope. Errors: none.
- **R3:** A maintainability finding alone cannot produce NEEDS_WORK unless it names concrete duplication in the plan, a named back-edge, or a named function absorbing new branching. Errors: none.
- **R4:** Named findings appear in the verdict artifact and as a one-line pointer in the spec's Decision Context. Errors: none.
- **R5:** No new canonical spec section; the spec template, capture, refine, and plan templates are unchanged (verified by diff). Errors: none.
- **R6:** The verification-spine page states the claim sentence verbatim. Errors: none.
- **R7:** The same sentence appears in the README and the docs home, byte-identical (verified by grep). Errors: none.
- **R8:** A FAQ entry cross-links the limit, and the existing "just tell it to write clean code" entry points at it. Errors: none.
- **R9:** No shipped copy claims the pipeline prevents, stops, or fixes maintainability decay (verified by grep for the claim verbs). Errors: none.
- **R10:** Withdrawn 2026-09-14. The "run it once and capture evidence" criterion is replaced by R12: a single run proves the section renders, not that it helps.
- **R11:** Downstream chain walked: repo docs, flow-next.dev (build green), AI x SDLC guide where it touches, vault Messaging Library and Release Timeline. Errors: none.
- **R12:** The technical refine pass asks the same two questions once and writes the answers into Decision Context through the existing write-back; no new section, no new flag. Errors: none.
- **R13:** Before any copy claims the section improves outcomes, a replay study on the fn-174 method (frozen specs, reviewer with and without the item, pre-registered bars, negatives retained) is recorded under agent-evals. Shipping the prose does not wait for it; claiming benefit does. Errors: none.

## Boundaries
<!-- scope: business -->

- No metric, evidence-JSON change, or per-module store (fn-143).
- No canary or weak-model extension test (fn-144).
- No merge gate, dashboard, score, or threshold.
- No new vocabulary; no new canonical section.
- No implementer-prompt changes: the measured result is that they move the intercept, not the slope.

## Decision Context
<!-- scope: both -->

**Why design time, and why two mouths.** Prompt-side pressure on the implementer is measured not to change the decay slope. Structure is decided before code exists, and since 5.0 the direct route means plan review is one of two places that happens; the technical refine pass is the other.

**Why the future-requirement question was dropped.** It is speculative by construction and sits opposite fn-174's shipped discipline that a task or surface not traceable to a stated requirement is a finding. Duplication that already exists in the plan and structure that is visible in the plan are the two questions a reviewer can answer without inventing a future.

**Why record rather than gate.** Neither model judgement nor static metrics have an established link to changeability. A gate that cannot be falsified becomes ceremony that consumes review rounds.

**Why the honest sentence ships now.** The limit is true today. When fn-143 lands it narrows from "does not prove" to "records the delta".

**Rejected: a new canonical section** (template migration across four consumers for a filing slot). **Rejected: making the section optional** (an optional structural question is not asked). **Rejected: claiming benefit from one run** (R10 withdrawn; R13 is the honest bar).

**Sources:** SlopCodeBench, arXiv 2603.24755v1; vault notes on the paper and on Horthy's software-factories series; fn-174's replay-campaign evidence for plan-review prose.

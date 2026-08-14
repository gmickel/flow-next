# fn-196-deferred-collapse-the-review-backend-to Deferred: collapse the review backend to one generic runner

## Goal & Context
<!-- scope: business -->

**Status: deferred stub. Research captured, no plan, deliberately not ready.** Written now so the research is not re-derived, and so the decision has a home when the surrounding work lands.

The review subsystem is the largest per-backend surface we own and the source of most recent external bug reports. Measured on current main: **2,362 review- and verdict-mentioning lines** in the CLI, **25 per-backend dispatch functions** across four bridged backends, and **2,569 lines** of review-skill prose. Each backend arrived with its own auth, delivery, streaming and failure quirks, and each quirk has cost at least one issue.

The question this spec exists to answer, later: can the *dispatch* half collapse to a single generic runner — run a command, capture its output, classify the verdict, write the receipt — while the *substrate* half stays exactly as it is?

The framing that motivates it: harnesses drive other CLIs well on their own, and a reviewer can already be steered by prompting, so much of the per-backend scaffolding may be paying for something the orchestrator would do anyway.

## Architecture & Data Models
<!-- scope: technical -->

Two halves, and they should not share a fate.

**The substrate must survive any change.** It is four releases of work and it is what makes a verdict trustworthy rather than narrated: the unchanged-artifact refusal that stops a re-review of identical input, deterministic round counting and the convergence ratchet, the attempt provenance rows that record work volume and where the judged head came from, honest failure classification that distinguishes a healthy reviewer producing no verdict from a transport timeout, and the merge gate binding a verdict to the exact head it judged. Prose cannot perform a compare-and-set on a receipt; whatever replaces dispatch inherits these unchanged.

**The dispatch half is the candidate.** A generic runner would take a command and a model from the consumer's own configuration, execute it once, capture output, classify the verdict against the existing grammar, and hand the substrate its receipt. Per-harness knowledge would move to recipes in the usage guide, where a harness's own invocation idiom already belongs.

**What must be measured before this is scoped**, because it decides whether the collapse is real: how much of those 25 functions is genuinely per-backend behavior versus accidental duplication. Known-genuine so far includes stdin-only prompt delivery for one backend, host project-doc suppression at the argv level for the same one, account-varying model identifiers for another, and a two-mode primary/legacy path for a third. A scout pass separates those from the rest; no size claim is credible before it.

## Edge Cases & Constraints
<!-- scope: technical -->

- **A same-family reviewer is not an independent verdict.** Any default that reviews in-session on the writer's own model gives up the property reviews exist for. One host already fails closed for exactly this reason because it has a single native family. A generic runner must keep it possible to reach a different family, and the tier vocabulary documents the rule.
- **Effort is not fungible across vendors** and stays pass-through.
- **Prompt templates are hash-pinned**; a collapse must not alter their bytes or the pins move for the wrong reason.
- **The receipt is the audit trail an autonomous loop reads.** Any change keeps its shape, or the loop's safety changes silently.
- Standing criteria in `.flow/criteria.md` apply as written and are not restated here.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A scout pass classifies every per-backend dispatch path as genuinely-per-backend or accidental duplication, with evidence per case, and states the honest size of the collapse. Errors: an unclassifiable path is listed as unknown rather than assumed collapsible.
- **R2:** The decision is recorded either way — collapse, or keep and simplify in place — with the reasoning and the measurement behind it. A deferral is also an acceptable outcome and is recorded the same way. No error surface.
- **R3:** If a collapse proceeds, the substrate is untouched: unchanged-artifact refusal, round counting and ratchet, attempt provenance, failure classification, and merge-gate head binding all behave identically, proven by the existing tests without weakening any of them. Errors: any test that needs an edit is justified explicitly, and an easier test after the change is treated as a regression.
- **R4:** If a collapse proceeds, cross-family reviewing stays reachable and the family rule stays documented. Errors: a configuration that can only reach the writer's family is reported, not silently accepted.

## Boundaries
<!-- scope: business -->

- No implementation in this spec. It is a stub carrying research and a decision.
- The verdict grammar, receipts, rounds and provenance are out of scope as change targets — they are the thing being protected.
- Not a change to how reviews are requested by users, and not a removal of the review step itself.

## Decision Context
<!-- scope: both -->

Deferred on 2026-08-14 by explicit decision, alongside the orchestration revamp that this would otherwise entangle. Sequencing reasoning: the orchestration spec moves model preferences into the consumer's instruction file, and the review backend is the one place a model identifier stays ours to record — so a collapse designed before that lands would be designed against a moving target.

**Rejected already: replacing the review backend with an in-session default at a different effort.** Same model, more tokens, same blind spots — the writer's family grading the writer. This is not a cost/benefit call; it removes the property the subsystem exists for.

Related work: the spec that removes packaged implementation delegation for the same more-agentic reason, and the orchestration-by-intent spec that defines the tier vocabulary this would consume.

## Parked unknowns

- The real size of the collapse. Nothing credible can be said until the R1 scout pass runs; the 25-function count is a surface measure, not a duplication measure.
- Whether the two-mode primary/legacy path for one backend should be collapsed or retired outright — a separate question that may be cheaper than the collapse itself.

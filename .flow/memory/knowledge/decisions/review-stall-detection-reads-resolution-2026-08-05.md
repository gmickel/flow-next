---
title: "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)"
date: "2026-08-05"
track: knowledge
category: decisions
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-168, fn-159, review-convergence, stall-detection, ratchet-prompt, findings-lineage, inference-vs-evidence]
applies_when: "a review loop runs to the cap with no early escalation and someone proposes re-adding a finding-count / severity-trend / new-blocker-twice stall rule"
decision_status: accepted
alternatives_considered: |
  - keep flat-trajectory, filter it to evidence-bearing opens (built, committed as 9417ba9b, then reverted): fixes one label, not the escalation
  - keep fresh-introduced-critical: fires on what every healthy thorough loop looks like
  - add a per-round-verification field to the digest: rejected, no new digest fields
  - lower the round cap instead of any early rule: partly adopted — the cap IS the aggregate bound now
---

## The decision

**Non-compliance now produces expensive answers instead of wrong ones.** That is the whole trade, and the direction of the flip is the point:

| a reviewer that resolves priors in prose | before | after |
|---|---|---|
| effect | priors carried at `open` → inflated open set → **false stall at round 2 of 8** — a *correctness* failure, silent, forcing a human to hand-verify | no lineage evidence → **runs to the round cap** — a *cost* failure, bounded and visible |

Correctness over cost, with the cap as the ceiling. Two heuristic stall classes are **deleted** from `_review_stall_rule`:

- the open-count / worst-severity **trend** rule (`flat-trajectory`), and
- the **presence-twice** rule (`fresh-introduced-critical`) — "each of the last two rounds raised a freshly introduced P0/P1".

`same-not-fixed-lineage` and the deterministic round cap are the only terminals. In exchange, resolution became **explicit**: the ratchet prompt states the machine grammar (`Prior finding #2: not-fixed`, or one `Prior findings: all fixed` line), the parser accepts every token the prompt advertises, and a drift guard (R6) now protects the one surviving terminal — a prompt/parser divergence no longer degrades a heuristic, it silently removes stall detection entirely.

## The historical hinge

`get_max_review_iterations()`'s own docstring, written when the cap was raised 4 → 8, is what motivated building these heuristics in the first place:

> The cap counts *dispatches*, which cannot distinguish a loop that is genuinely stuck from one converging in severity while each fix surfaces one more small thing. Field evidence: in a single session three specs hit the cap at 4, and in every case the findings remaining were trivial residue - two were reset by a human and shipped almost immediately after.

That observation is correct, and it is exactly why the heuristics are now retired: **the answer was better evidence, not better inference.**

## The two transcript observations that settle the `unaddressed` question

The originally-specified aggregate signal was `unaddressed: []` from the closing JSON tail. It is unsound, and not marginally so. Observed in fn-168's own plan-review rounds:

- **round 1** tail: `{"classification_counts":{"introduced":3,…},"unaddressed":["R1","R3","R6"]}` — a round where **no prior findings existed at all**;
- **round 3** tail: `{"unaddressed":[]}` — a SHIP with **zero discussion of priors**.

The key is **ambient** — emitted by every review regardless of whether it says anything about prior findings — and it answers a different question (which spec R-IDs the review left uncovered). A prior *finding* is not an R-ID, so a legitimately empty array can coexist with a genuinely unfixed finding. Under this design that is fatal rather than sloppy: `same-not-fixed-lineage` reads `not_fixed` and nothing else, so an ambient signal sweeping priors to `fixed` would **erase the only evidence stall detection has left** — no class could ever fire, and every pathological loop would run to the cap with no diagnostic. Hence a dedicated line-family record (`Prior findings: all fixed`), which only an actual statement about priors can produce.

## The empirical asymmetry

**3 recorded false positives, 0 recorded true positives** for either deleted class.

The false positives were three consecutive flow-swarm specs (fn-156, fn-157.2/fn-158.2 impl, fn-158 completion), each escalating at round **2 of 8** while visibly converging (6→1, 7→2 findings). Every one was hand-verified by a human and shipped. The causal chain, verified against live digests in flow-swarm's `fn-158-…json` → `review_attempts`: the ratchet asked reviewers to state whether each prior was "fixed or not-fixed" but never stated the line grammar → codex complied *semantically* (prose, a requirements table, `"unaddressed": []`) and emitted zero parseable records → `_review_finding_prior_items` updated no statuses and carried all six priors forward at `open` → the digest showed 6 carried + 1 genuinely new = 7 open against the prior round's 6 → the trend rule saw no strict improvement and stalled.

**Honest caveat, which must not be lost: churn is real.** `knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04` documents non-convergence in the wild. But that is the **PR review-bot channel**, bounded by `land.ciFixBudget` + unresolved-thread count + the patience window, all owned by `/flow-next:land` — a separate channel that never participates in the findings container, the digest, the lineage, or any flowctl guard. "We deleted the rules" does **not** mean "we decided churn is a myth."

## Why the survivor is different in kind

Both deleted rules were **round-local snapshots inferring convergence** from data the parser never reliably captured — a count/severity trend, and two independent `any()` calls with no cross-round linkage. The presence-twice rule in particular fires on what every healthy thorough loop looks like (a new P1 found and fixed in each of two rounds) and never checks whether anything was *resolved*.

`same-not-fixed-lineage` reads a **statement**: `not_fixed` is written only by an explicit parsed per-ordinal resolution line. Two corrections were needed to make that literally true rather than nearly true:

1. **fn-168.1** — the prompt advertised the hyphen (`not-fixed`) that `_FINDINGS_PRIOR_RE` rejected (it spelled `not[\s_]fixed`). A compliant reviewer would have forced a record/canonical count mismatch and had the whole round's findings container discarded, silently. Whatever the prompt advertises must parse; R6 is the standing guard.
2. **fn-168.2 (R8)** — carry-forward propagated `status` verbatim, so a `not-fixed` stated once in round 2 and merely *omitted* in round 3 sat at `not_fixed` in **both** digests and escalated a round that had said nothing. A carried `not_fixed` now reverts to `open` before the round's own records apply (`fixed`/`withdrawn` preserved as resolved terminals), so an intersection means the reviewer said "still broken" in two consecutive rounds.

## Accepted consequences — these are the decision, not oversights

- **(a) fn-159's cost claw-back for non-repeating loops is reverted.** fn-159 built these rules to "claw back the doubled worst case of the 4→8 raise". Honest framing: a bounded insurance premium — worst case single-digit-millions of tokens on a genuinely pathological loop (observed: one codex plan-review = 0.9–1.8M input tokens) — paid to stop taxing healthy loops, which field data says are overwhelmingly the common case. If the premium bites: **lower the cap, never re-add inference.** fn-168.5 added `review.maxIterations` precisely so that instruction is reachable (it was env-only and unpersisted before).
- **(b) Non-repeating churn loses early detection entirely** and is cap-bounded by design. This is the regression vector. Stated so nobody re-adds a trend rule.
- **(c) Backend switches lose all early detection.** `same-not-fixed-lineage` is gated on `same_identity` (backend + reviewKind); the trend rule was the aggregate fallback that stayed live across switches. Switches are cap-only now.
- **(d) The host backend is cap-only in practice.** Host reviews never pass through the ratchet builder, so they produce no lineage evidence unless the host reviewer follows the grammar stated in the three `workflow-host.md` files, and nothing enforces that. The open question about host-reviewer compliance rose from "nice to have" to "the only backend with no stall coverage."
- **(e) A `not_fixed` status no longer survives an unrepeated round** (R8), so the rendered prior-findings block shows such an item as `open` and loses the "you called this unfixed last round" nuance. Accepted: that is prompt copy, not evidence, and the alternative was a new per-round-verification digest field.

## Supersession

**fn-159 R2 is superseded** for the two deleted classes. It enumerates all three stall rules with their exact math as an acceptance contract; only `same-not-fixed-lineage` survives, and it now depends on the R8 carry-forward reset that fn-159 did not have. fn-159's other machinery — the cumulative counter, the pre-dispatch reservation/refund, the artifact-unchanged guard, transport-health, and the human-only reset verbs — is untouched.

## If you are here because a review loop ran to the cap

That is the expected shape for a reviewer that does not use the grammar. Before touching `_review_stall_rule`:

1. check whether the reviewer emitted any `Prior finding #N: <status>` lines at all — if not, the fix is prompt/backend compliance, not a new rule;
2. if the cost is the problem, lower `review.maxIterations`;
3. if you are convinced an early rule is needed, it must read an explicit reviewer statement. A count, a severity trend, or "it happened twice" is the thing that produced 3 false positives and 0 true ones.

Related: [[structured-review-parsers-must-2026-07-30]], [[pr-bot-review-loops-do-not-converge-2026-08-04]], [[test-production-path-not-parallel-construction-2026-05-21]].

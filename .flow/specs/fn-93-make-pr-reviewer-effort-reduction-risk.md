# make-pr reviewer-effort reduction: risk-ranked review surfacing + reviewer guidance (get to the 20%)

> **STUB** — captured 2026-07-10 from external-team field feedback (an external team's AI-SDLC weekly; their head of software engineering). As agentic throughput rises, PRs get bigger and more numerous (one product team: "wesentlich mehr Code, größere PRs"). Reviewers don't know **where to look** — the promise from Gordon's coaching slide is that a human only has to read the **~20-30%** that actually needs review. make-pr should render the PR so the review lands on the risky minority, and coach the reviewer on HOW to review under the new model. **Complements fn-86** (the deterministic removed-export-refs + `evidence.files` traceability slice) — this is the broader review-surfacing / prioritization + reviewer-guidance layer on the same structured payload. Refine via `/flow-next:interview` before planning.

## Goal & Context
<!-- scope: business -->

The pipeline already produces a structured PR body (cognitive-aid) plus a cross-model review, so confidence on most of the diff is high. What's missing is **explicit reviewer prioritization**: which files/changes carry the risk, what a human must actually verify by hand, and what is safe to skim — so review effort collapses to ~20-30% without the reviewer guessing. Two field asks: (1) surface and rank the risky minority; (2) tell reviewers *how* to review now (it is still a manual step, but they don't yet know where to point their attention). Machine reviews / bots add safety, they do not replace the human — the human still enters, just efficiently.

## Architecture & Data Models
<!-- scope: technical -->

TBD (interview). Built on the existing `export-cognitive-aid` payload + make-pr render (see fn-86). Candidate pieces:

- **Risk-ranked review surface** — order / annotate changed files by review-priority signals that are already deterministically computable (security-sensitive paths, public-export / API changes, removed exports, large hunks, no-test-touch, R-ID-coverage gaps) so the body says "start here → these N files carry the risk → the rest is mechanical."
- **Reviewer-guidance block** — a short, standard "how to review this PR" section (what to verify by hand vs trust the cross-model review + bots for), tuned to the change shape; the counterpart to make-pr's existing verification / review-plan sections.
- **Large-PR degradation** — the current path (and Linear's **Guide** grouping) breaks on very large PRs ("PR zu groß, ich kann nichts machen"); define graceful behavior — chunk / group by feature-area, or emit a "split this PR" recommendation — rather than giving up.
- **(Coverage, related)** — much of the value only lands if **all** PRs route through make-pr even when the code was hand-written, so the body + tracker write-back stay consistent. Whether make-pr nudges / normalizes a hand-made PR is an open scope question (may be its own item; capture the dependency, don't silently absorb it).

## API Contracts
<!-- scope: technical -->

TBD at planning. Anchor points: the make-pr workflow render (verification / review-plan / critical-changes sections), the cognitive-aid payload fields (reuse fn-86's `removed_detail` + `evidence.files`, plus `diff_summary` + the security-sensitive-path detection), and any Linear "Guide" grouping seam. Cross-platform parity via `sync-codex.sh`.

## Edge Cases & Constraints
<!-- scope: technical -->

- Risk ranking must trace to flowctl-computed fields — no agent narration of "what the code does" (make-pr's anti-fabrication stance; same discipline as fn-86).
- Reviewer guidance must NOT imply the human can skip review — it re-points attention, it never green-lights auto-merge.
- Large-PR handling must never **silently** truncate the review surface — flag what was elided.
- Do not duplicate fn-86 — build on its computed fields.

## Acceptance Criteria
<!-- scope: both -->

- **R1 (STUB):** make-pr renders a **risk-ranked review surface** (which files/changes to review first, what is mechanical) from deterministic payload signals.
- **R2 (STUB):** make-pr includes a **reviewer-guidance** block (what to verify by hand vs trust the automated reviews), tuned to the change shape.
- **R3 (STUB):** defined **large-PR behavior** (feature-area grouping and/or a "split this PR" recommendation) instead of a hard failure; anything elided is flagged.
- **R4 (STUB, related):** capture the "all PRs via make-pr even when hand-coded" coverage / write-back concern as a tracked dependency or sibling scope.
- *(Real R-IDs assigned at planning; reconcile numbering with fn-86 if the two are merged.)*

## Boundaries
<!-- scope: business -->

- In: reviewer-effort reduction via risk-ranked surfacing + reviewer guidance + graceful large-PR handling, on the existing structured payload.
- Out: the deterministic removed-export / `evidence.files` traceability already scoped in **fn-86** (reuse, don't redo); auto-generated review *comments* or a second-model review pass (make-pr's stance: the structured body does the lifting); productivity measurement.
- GitHub-first; GitLab MR parity is tracked in **fn-73**.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->
Agentic throughput has moved the bottleneck to human review; the offering's promise ("only review ~20%") only holds if make-pr actively points the reviewer at the risky minority and coaches the new review habit. fn-86 made individual claims traceable; this makes the *whole PR* triageable, so human review scales with agentic output.

### Implementation Tradeoffs
<!-- scope: technical -->
TBD (interview). Open: which risk signals to rank on and how to weight them; how much to lean on Linear's Guide grouping vs render our own surface; where the "split this PR" threshold sits; how much of the reviewer-guidance is static vs change-shape-driven. Gordon is collecting field experience reports first.

## Strategy Alignment
- **Review-throughput / cognitive-aid** track — extends make-pr from "trustworthy claims" (fn-86) to "triaged review" so human review scales with agentic output.

## Conversation Evidence
> Field origin — external-team AI-SDLC weekly, 2026-07-10 (head of software engineering): "[at one product line] merkt man deutlich, wesentlich mehr Code, größere PRs … du hast auf deiner Folie gezeigt, dass man nur noch 20% anschauen muss … wie man dann wirklich einen PR reviewt, wo soll er genau reinschauen?" Gordon: make-pr should already formulate the PR to be review-friendly (cross-model review at PR level → high confidence → review the 20-30%); Linear's Guide groups PRs by feature area (breaks on huge PRs); ensure all PRs route via make-pr even when hand-coded (write-back); make the work-skill next-step messages clearer; bots add safety, they don't replace the human. Detailed notes in the maintainer's vault (AI-SDLC weekly 2026-07-10).

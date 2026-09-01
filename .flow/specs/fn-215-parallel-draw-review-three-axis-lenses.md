# Parallel-draw review: fan out three axis lenses, merge, fix once

## Conversation Evidence

> user (turn A): "so we already know we want to be maximially agentic right, we do not give diffs etc"
> user (turn B): "but why is this an issue are reviewers currently reraising things that were already fixed or what is happening"
> user (turn C): "so we want to get rid of this iterative behaviour, keep quality but use prose and other methods to get it to try to raise all issues at once?"
> user (turn D): "so you want to do 3 parallized reviews?"
> user (turn E): "i thought we already had a 2 axis split somewhere?"
> user (turn F): "run the eval, record economics, tokens and wall clock too so we can make a decision if it pans out"
> user (edit cycle 1): "we did do testing and can say that this change is expected to dramatically shorten and remove the iterative churn or something simmilar"
> user (turn G): "yes, but a couple of thoughts before you capture. The economics piece is ok but we can also teach people how to avoid this in the cookbook and in the relevant documentation pages (positive formulation again), such as they could say, flow-next:work on ... use 1 reviewer instead of 3. they could also go further and say, use 3 different models from different families during the review fan out. all of this is possible without us adding anything to the fan out implementation through simple prompting. and ofc reviews are optional anyhow"

## Goal & Context

<!-- Goal & Context: 80% [paraphrase] (turns C, D, G anchor intent), 20% [inferred] (study facts) -->

Review findings arrive serialized today: each fix-loop round re-reviews the whole artifact and surfaces a thin sample of the real finding set, so converging costs many push→review→fix round-trips (observed: 12–14 rounds on recent prose-heavy work). Two pre-registered studies established the mechanism and the remedy: single-pass review recall is stochastic sampling (~45% of validated findings per draw), narrowing the reviewed diff loses integration findings (parked), and a union of three concurrently-dispatched draws recovers 1.4–1.6× single-draw recall at flat validity — with axis-differentiated draws the only arm clearing the pre-registered ship bar and the only one catching keys every identical draw missed. The change: the per-task implementation review and the standalone review dispatch fan out three concurrent draws by default — one per fixed axis lens — and the conductor merges them into one consolidated finding set for one fix pass per round. Measured against historical rounds, this change is expected to dramatically shorten the iterative review churn — most of what previously surfaced across many serial rounds is available in the first merged round. [paraphrase]

## Acceptance Criteria

- **R1:** The impl-review and standalone-review dispatch runs three concurrent reviewer draws per round by default, on the same resolved backend/model the single dispatch uses today, each draw differing from the base prompt by exactly one added axis line: correctness-and-logic of the changed code; contracts-and-consistency (do docs, tests, and stated promises agree with what the code does); integration-with-unchanged-code. [paraphrase]
- **R2:** Draws receive the review scope by identity (base ref / range in the repository), never an embedded diff or file payload — the existing prompt contract, preserved across the fan-out. [paraphrase]
- **R3:** The conductor merges the draws: same-defect findings dedupe to one entry (judgment-based; deterministic identity is a later hardening), findings failing the evidence bar are dropped with a count, and the merged set renders ranked with an Act-On tier capped at 5 plus a published remainder — considered-and-deferred is distinguishable from never-seen. [paraphrase]
- **R4:** One consolidated fix pass per round; every other fix-loop semantic is unchanged — SHIP gate, deterministic round cap, receipts recording what actually ran. A merged round consumes one review round in the counter, not three. [inferred]
- **R5:** Natural-language steering works without any new flag or config key: an instruction like "use 1 reviewer instead of 3" collapses the round to a single draw, and "use three different model families for the review fan-out" routes the draws cross-family — both resolved through the existing routing precedence (explicit instruction wins), prompting only. [paraphrase]
- **R6:** Documentation teaches the dials in positive formulation: a cookbook recipe plus the relevant reference pages cover the default, the single-reviewer economy phrasing, and the cross-family upgrade phrasing — framed within reviews being optional to begin with. [paraphrase]
- **R7:** Completion review, the land loop, and external bot reviews are untouched; no config keys, no dual topology — the fan-out is the one shape, steered only by prose. [paraphrase]
- **R8:** Codex mirror regenerated (sync-codex twice, idempotent), skill-contract tests cover the fan-out prose (three-axis dispatch present, merge step present, steering phrasings honored), and the repo CHANGELOG gains an Unreleased entry. [inferred]
- **R9:** The merged round's verdict is synthesized mechanically from the draws' verdict tags under the existing precedence (NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > all-SHIP) — worst wins; no draw's verdict is judged away. [inferred]
- **R10:** Partial fan-out fails open: the merged round proceeds from whichever draws returned a verdict (one is enough), the receipt records how many draws failed, and only an all-draws-no-verdict round is a transport failure with today's durable refund semantics. No error surface beyond that: a failed draw never blocks, retries, or consumes extra rounds. [inferred]
- **R11:** Scope of the fan-out: the codex and host backends, on the FIRST review round of a scope; re-review rounds after fixes resume a single primary session (the correctness axis) carrying the merged prior-finding set through the existing ratchet grammar. rp keeps its single stateful chat; copilot and cursor keep single dispatch in this change (same pattern available later). Exactly ONE round reservation wraps the whole fan-out (standalone reviews continue to reserve none), and the artifact-identity hash is computed once per merged round. [inferred]
- **R12:** The merged receipt lands at the existing path with the existing top-level schema (mode, verdict, session_id and model = the primary draw's) plus a draws array honestly recording each draw's model, session, verdict, and axis; per-draw raw outputs persist beside the receipt for audit. Receipt-path collisions are impossible by construction (per-draw temp paths derived from the task id + axis). [inferred]
- **R13:** The merged round counts 1:1 against review.maxIterations — the cap bounds rounds, not draws. [inferred]

## Boundaries

- Fixed default of three draws — no k knob, no per-repo config; deviation is a per-invocation prose instruction. [paraphrase]
- The residual is real and stated honestly in docs: roughly a third of validated findings eluded every draw in the studies — round 2 shrinks, it does not disappear. [inferred]
- Cost on clean diffs is deliberately accepted: a change that would have shipped in one round pays ~3× review tokens; the documented economy phrasing is the remedy, not a knob. [paraphrase]
- Deterministic finding identity, receipt integrity, and cross-round memory are out of scope (the planned receipt-hardening work consumes this merge step later). [inferred]

## Decision Context

- Evidence base: `~/work/agent-evals/studies/review-churn-scoping-2026-09` (delta-scoping PARKED — integration recall loss) and `~/work/agent-evals/studies/parallel-draw-review-2026-09` (axis-3 union 12/17 validated keys vs 45.1% single-draw mean = 1.56×, pre-registered bar 1.5×; iid-3 1.43×; validity flat; economics recorded per draw). Settled: fan out, don't scope down.
- The axis-vs-iid margin is one finding on a 17-key sample; the load-bearing decision is three-draw union vs single draw (robust across arms and studies). Axis lenses are the evidence-favored default and cost nothing; not worth re-litigating either way.
- The two-axis quality-auditor (work Phase 4) keeps its verbatim-two-reports contract — it feeds a human-shaped judgment. The fan-out draws merge because they are k samples of one finding distribution feeding one fix pass. Same dispatch pattern, deliberately different consumption contract.
- Economics posture per the maintainer: teach, don't knob — the cookbook and reference pages carry the steering phrasings; the implementation adds no configuration. Reviews are optional to begin with, so the fan-out is a property of a layer the repo already opted into.
- Triage load (~11 unique findings per merged round in the studies) is why the Act-On cap and published remainder land in this spec rather than as separate polish.

## Decision Context (planning resolutions — settled)

- Deterministic-vs-judgment split for the fan-out: flowctl owns concurrency (three backend dispatches inside one command invocation), per-draw receipt paths, mechanical verdict synthesis from tags (R9), and the merged receipt write; the host coordinator owns the FINDING merge — same-defect dedupe, evidence-bar drops, Act-On ranking — which is judgment. Mirrors the sanctioned subprocess-LLM carve-out.
- First-round-only fan-out (R11) is the cost architecture: the studies show the harvest value is the first merged round; re-review verifies fixes and needs continuity, not breadth. This also dissolves the three-session resume problem — one primary session resumes.
- Axis lines enter the rendered prompt through the template layer, so the template-parity and hash-pin suites update in the same commit with rationale (test_prompt_text_pinned contract).
- The quality-auditor two-axis contract (test_two_axis_audit_contract) is a tripwire, not a target — its verbatim-two-reports rule is untouched.
- Sequencing with open work: fn-191 (review-terminal extraction) touches the same flowctl region — whichever lands second rebases; fn-198's journal-wedge hardening is adjacent to the finalization leg the fan-out exercises — its invariants must hold with draws collapsing into one round; read fn-157's visibility stub before building the concurrent dispatch.
- The ratchet/prior-finding grammar consumes the MERGED findings container from round 1 — re-checked against the stall-detection decision entry (review-stall-detection-reads-resolution-2026-08-05).
- Memory priors honored: receipts dropped between rounds break confabulation (drop-receipt-to-break-codex-2026-05-09) — the primary-session resume carries findings via the ratchet, not accumulated raw transcripts; parsers distinguish invalid from absent (structured-review-parsers-must-2026-07-30).

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_template_parity test_prompt_text_pinned test_review_receipt_schema test_review_convergence_cap -q`
- `./scripts/sync-codex.sh` twice, idempotent
- `uvx ruff@0.16.0 check .`

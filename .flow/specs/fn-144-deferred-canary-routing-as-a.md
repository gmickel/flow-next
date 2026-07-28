# fn-144 DEFERRED: canary routing as a maintainability oracle

> **STATUS: DEFERRED, do not plan or implement.** Parked by Gordon on 27 Jul 2026 as too complex to put in front of users right now. Captured so the design is not lost and not re-derived from scratch. Revisit only on an explicit decision; the trigger conditions are named in Boundaries.

## Goal & Context
<!-- scope: business -->

The strongest known oracle for "did the agent leave maintainable structure" is not a metric and not a model's opinion. It is an experiment: **give the codebase to a weaker model and see whether it can extend it.** Unmaintainable structure is precisely what a weaker model cannot navigate, so the weak model's success rate on change N+1 scores the strong model's work on changes 1..N.

Dex Horthy proposed this against [SlopCodeBench](https://arxiv.org/html/2603.24755v1) (Part 3, Jul 2026): have a frontier model write checkpoints 1..N, then see whether a cheaper model can implement N+1, which amplifies the maintainability signal that pass rates hide. It is deterministic, runs unattended, and beats asking a model whether code looks clean - the paper's own logic says a model that could reliably tell good structure from bad would have written good structure.

Flow-Next is unusually well placed to run it, because `.flow/` already holds the ordered sequence of completed specs per module and per-stage model routing already exists.

## Architecture & Data Models
<!-- scope: technical -->

Two variants were considered. **The cheap one is the one to build if this is ever revived.**

**Variant A - historical replay (rejected as the starting point).** Reconstruct the workspace as of spec N, then replay spec N+1 against it with a weaker model and score by the spec's own acceptance criteria. Faithful to the benchmark, and it needs git time travel: checkout the parent state, strip later work, re-run, discard. Brittle across squashes, rebases and dependency drift, and expensive to keep working.

**Variant B - canary routing (preferred).** Do not reconstruct anything. Deliberately route an occasional **real** spec on a mature module to a weaker model, and record whether it landed with evidence, how many review rounds it took, and its token cost. No time travel, measures the live codebase rather than a reconstruction, and rides work that was happening anyway. The trade: it is opportunistic - readings arrive when work touches that module, not on demand.

Sketch for variant B:

- Module-level canary policy: eligibility (module has at least K completed specs), rate (at most 1 in N specs), and an opt-out for anything risk-tiered above a threshold.
- Reading: `{spec_id, module_key, canary_model, landed: bool, review_rounds: int, tokens, wall_clock}` appended next to the fn-143 quality series so the two can be read together.
- Report: canary landing rate and cost per module over time, alongside the erosion/verbosity trend. A module where the weak model used to land and now cannot is the signal worth paging a human for.

## API Contracts
<!-- scope: technical -->

Not designed. If revived, expect a `flowctl canary` surface parallel to `flowctl quality`, and reuse of fn-143's store layout so both series share a module key.

## Edge Cases & Constraints
<!-- scope: technical -->

- **User comprehensibility is the reason this is parked.** "We sometimes deliberately use a worse model on your real work" is a hard sentence to put in front of an adopter, however sound the measurement logic is. Any revival needs the framing solved before the code.
- **Never on risk-tiered-critical work.** A canary must not be the reason a security-sensitive or customer-facing change is implemented by a weaker model.
- **Confounds are real.** A canary failure may reflect spec quality, task sizing or model regression rather than codebase structure. A single reading is not evidence; only the trend across a module is.
- **Cost is not zero.** A weak-model attempt that fails may consume review rounds and then need re-running with the normal model. Budget it explicitly, or the instrument costs more than the insight.
- **Selection bias.** If canaries only ever land on easy specs, the reading is flattering and useless. Eligibility has to be structural, not convenient.

## Acceptance Criteria
<!-- scope: both -->

*(Intentionally empty. Not planned, not implemented. Write criteria at revival, when the framing question in Edge Cases has an answer.)*

## Boundaries
<!-- scope: business -->

- **Out of scope now, by decision.** Do not plan, do not break into tasks, do not implement. This spec exists to preserve the design.
- **Revisit triggers, any one of:** (1) fn-143's erosion/verbosity trend proves too weak to inform real decisions and a stronger oracle is needed; (2) a portco or client explicitly asks for a maintainability measurement stronger than a static trend; (3) the adopter-facing framing problem gets a clean answer, at which point variant B is cheap.
- **If revived, start from variant B.** Variant A's historical replay is documented above only so nobody re-derives and re-rejects it.

## Decision Context
<!-- scope: both -->

**Why parked rather than dropped.** The measurement logic is the best available, and it would be expensive to rediscover. The blocker is not technical soundness, it is that the instrument is hard to explain to the person whose repo it runs in.

**Why variant B over variant A.** Historical replay buys fidelity to the benchmark and costs brittle git plumbing that must keep working across squashes and rebases forever. Canary routing gets most of the signal from an instrument that is almost entirely a recording decision on top of routing that already exists, and it measures the codebase people actually work in.

**Relationship to the shipping work.** fn-142 names structural risk at plan review; fn-143 records a deterministic trend in the receipt. This spec would have been the strongest of the three and is the one a user would find hardest to accept, which is why it is last.

**Source:** [[Agentic SDLC - SlopCodeBench (Orlanski et al., Mar 2026)]] "Horthy's proposed better oracle"; Horthy Part 3, https://x.com/dexhorthy/article/2081797628552270027.

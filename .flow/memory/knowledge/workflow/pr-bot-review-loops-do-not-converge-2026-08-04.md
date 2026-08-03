---
track: knowledge
category: workflow
module: review-subsystem
tags: [bot-review, land, convergence, triage, severity-inflation]
status: active
---

# PR-bot review loops on state-machine code do not converge - cut on reachability, not on a clean round

**What happened (fn-159, PR #290, 2026-08-03/04):** the Codex PR bot reviewed a
new review-terminal state machine for ELEVEN rounds and produced fresh P1s
every round (counts 2,1,3,2,3,4,1,2,4,3,6 - flat-to-rising). Every finding was
technically true; each fix opened a narrower crash-window or guard-bypass
finding. Even a dedicated adversarial pre-emption pass (which out-found the bot:
1 P0 + 9 more, all fixed pre-commit) did not reduce the next round's count.
The bot has no cost function: it reports anything true at P1 forever,
regardless of reachability or recovery cost.

**Why:** concurrency/crash-window state machines have an effectively unbounded
supply of true-but-vanishingly-reachable findings, and shell-guard hardening is
a formally unwinnable arms race (documented in ralph-guard's threat model).
"Loop until the bot goes quiet" is not a terminating strategy on this class of
code.

**How to apply:**
- Cut on REACHABILITY + RECOVERY, not on bot silence: decline (with reasoned
  replies) findings that require multi-condition crash interleaves or
  adversarial shell construction when the worst case is bookkeeping recoverable
  by a documented human verb. Apply fn-159's own test: does the finding name a
  concrete bad outcome at realistic reachability?
- The first 2-3 rounds are gold (real defects); expect diminishing returns
  after ~round 4-6 on state-machine diffs. Severity labels from the bot are
  inflated relative to the outcome-anchored P0-P3 definitions - re-tier before
  treating as blocking.
- A self-run adversarial pre-emption pass (fresh reviewer told to hunt the
  bot's find-classes: crash windows, interleaves, parity gaps, guard shapes)
  is worth one round's cost and catches P0s the bot misses - but it does NOT
  make the next bot round clean; budget accordingly.

**Deferred, watch for in the field (declined PR #290 round-11 threads, fix if
symptoms appear):**
1. Re-plan reset does not discard consumed-but-unpublished journals
   (symptom: stale journal replayed after `spec reset-review-rounds`).
2. Superseded receipt-bearing finalization when the receipt target was never
   created (symptom: retained journal / repeated REPLAY_REQUIRED after a
   concurrent same-type SHIP).
3. Byte-exact `review-rounds record` retry after lost output drops the
   superseded flag from the summary (symptom: a late pre-SHIP verdict briefly
   reported as live; durable state stays correct).

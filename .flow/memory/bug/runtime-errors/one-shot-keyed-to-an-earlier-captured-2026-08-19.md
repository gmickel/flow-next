---
title: "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release "
date: "2026-08-19"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-land/workflow.md
tags: [fn-200, land, one-shot, concurrency, claim-dir, codex-review, review-feedback]
problem_type: runtime-error
symptoms: "Codex NEEDS_WORK x2: claim covered gate-judged head while mutations could hit a moved head; transient gh read failure consumed the head's one shot"
root_cause: claim-then-act with no re-validation of the key; unreadable folded into mismatch; report field initialized inside a skippable gate
resolution_type: fix
related_to: [bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27]
---

## Problem
fn-200.2 added a one-shot-per-head Phase 3 action to the land workflow (`request-reviewers`): atomic `mkdir` claim keyed to `(PR, HEAD_OID)`, then remote mutations, then a ledger write. Codex impl-review returned NEEDS_WORK twice on the same shape: (1) the claim covered the head Phase 2 judged while the mutations could land on a head that moved in between (exact-once broken, un-gated head flipped ready); (2) after adding a head re-read, a transient gh failure (empty read) took the "moved" branch and left the fresh claim dir behind - every later tick then saw `already:` and the head's one shot was consumed by a transport blip. A third finding (P2) caught that the per-PR report field was initialized inside the gate, so early-exit gates (durable label, CI red, QA) emitted a stale/empty value in multi-PR ticks.

## What Didn't Work
Treating "claim, then act" as sufficient for a one-shot keyed to a SHA captured earlier, and folding "unreadable" into "mismatch" with one `[[ -z || != ]]` test.

## Solution
workflow.md §3.4b: claim -> re-read `headRefOid` -> three-way split: unreadable => `rmdir` this tick's claim, `failed:` + RESOLVING (retry allowed); moved => no mutation, claim kept (inert, names a dead head), RESOLVING; equal => proceed. `REVIEWERS_STATE=off` moved to the PR_STATE capture at the top of Phase 2. Static test pins the token ORDER claim < head re-read < rmdir < `gh pr ready` (commits 3cf542be, next).

## Prevention
For any one-shot keyed to state captured in an earlier phase: (a) re-validate the key after taking the exclusion primitive and before the first mutation; (b) treat "could not read" and "read a different value" as different branches - only a confirmed mismatch may leave a durable marker, a read failure must release it; (c) initialize every per-PR report field at PR-state capture, never inside a gate that early exits can skip. Cheap check before review: source the snippet with a stubbed `gh` and run the race/failure cases (see .flow/tmp sim pattern).

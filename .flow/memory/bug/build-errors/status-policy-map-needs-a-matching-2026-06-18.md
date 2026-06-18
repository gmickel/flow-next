---
title: Status-policy map needs a matching reconcile-loop branch per rung (map ≠ write)
date: "2026-06-18"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
tags: [fn-66, tracker-sync, status, reconcile, who-wins, in-review, merge-evidence, rp-review]
problem_type: build-error
symptoms: "new normalized rung mapped in the table but unreachable — reconcile loop had no branch, setStatus never fired"
root_cause: edited the flow→normalized table + fixtures without adding the matching reconcile-loop branch; fixture asserted a setStatus the loop couldn't produce
resolution_type: fix
related_to: [bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10]
---

## Problem
A status-policy reference table can map a flow state to a normalized rung (e.g. open PR → `in-review`) while the *reconcile loop* that actually writes status has NO branch for that rung — so the projected status silently falls through to the conflictTiebreak default and never drives a `setStatus`. fn-66.1 added `flowToNormalized(spec, prEvidence)` mapping open-PR → `in-review`, but the `reconcileStatus` if/elif ladder had no `flowNorm == in-review` branch. Fixture S-H asserted `setStatus(in-review)`, contradicting the loop. RP impl-review caught it (NEEDS_WORK).

## What Didn't Work
Editing only the flow→normalized lookup table and the fixtures. A who-wins/reconcile policy has TWO layers — the mapping (what a state *means*) and the loop (what to *write*). Changing the map without adding the matching loop branch leaves the new rung unreachable.

## Solution
For every new normalized rung the map can emit, add a matching explicit branch in the reconcile loop, ordered correctly against the existing deadlock-first / terminal-wins rules. Also: a "preserve existing state" nuance that lives only in a fixture must be promoted to a real loop branch (S-G: prEvidence=none projects in-review but must NOT force a downgrade — needs its own guarded branch checked BEFORE the generic in-review push). And model ALL probe outcomes as explicit enum values (added `ambiguous` + `probe-error` alongside merged/open/closed-unmerged/none) so unknown-branch / gh-failure routes to non-terminal+NEEDS_HUMAN rather than being mistaken for `none`/`merged`. status-sync.md reconcile loop + flow→normalized table + fixtures S-G/S-J.

## Prevention
When editing a status/who-wins policy that has a mapping table AND a reconcile loop: every rung the table can emit needs a corresponding loop branch that decides whether/what to write, ordered against the collision-first rules. A fixture asserting a `setStatus(X)` is the oracle — grep the loop for a branch that produces X before shipping. Model probe/evidence inputs as an exhaustive enum (including the failure/ambiguous cases), never just the happy buckets.

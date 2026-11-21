---
title: Do not combine GraphQL PR reply and resolve in one mutation
date: "2026-11-21"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-resolve-pr/scripts/reply-to-pr-thread
tags: [graphql, resolve-pr, partial-success]
problem_type: integration
symptoms: resolveReviewThread can succeed after addPullRequestReviewThreadReply fails in a single GraphQL mutation
root_cause: GraphQL executes top-level mutation fields serially and does not abort later fields on field-level error
resolution_type: fix
related_to: [bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17]
---

## Problem
Combining `addPullRequestReviewThreadReply` and `resolveReviewThread` in one GraphQL mutation broke the invariant that a PR review thread is never resolved without a posted reply. GraphQL executes top-level mutation fields serially and continues after a field error, so `resolveReviewThread` can still succeed after `addPullRequestReviewThreadReply` fails.

## What Didn't Work
Adding a `--resolve` flag to `reply-to-pr-thread` that sent both mutations in a single `gh api graphql` request saved one round-trip, and Codex implementation review flagged the partial-success failure mode as a P1 defect.

## Solution
Kept `plugins/flow-next/skills/flow-next-resolve-pr/scripts/reply-to-pr-thread` and `resolve-pr-thread` as two separate commands so `resolve-pr-thread` runs only after the reply command exits 0.

## Prevention
Never combine dependent write mutations in one GraphQL request when the second mutation depends on the first succeeding. Gate the second mutation on the first command's exit status and response payload.

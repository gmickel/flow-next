---
title: Test asserted a public envelope that never carried the field
date: "2026-08-01"
track: bug
category: test-failures
module: plugins/flow-next/tests/test_chart_briefing.py
tags: [chart, test-design, review-feedback, api-surface, scope]
problem_type: test-failure
symptoms: Test invokes chart show --json but reads the asserted values from the sidecar; review flags the contract as unpinned
root_cause: Spec prose named chart show --json as the home of per-briefing status; that projection only carries briefing_count
resolution_type: fix
related_to: [bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02, bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09, bug/test-failures/test-production-path-not-parallel-construction-2026-05-21]
---

## Problem

A spec criterion said per-briefing `status` in `chart show --json` "remains the single
source of truth for capture-readiness". `chart show --json` carries no per-briefing
status at all - `compact_chart_metadata` projects `briefing_count` and nothing else. The
test written against that sentence called `chart show --json`, asserted only
`briefing_count`, then read the actual statuses from the chart sidecar. Review (rp) caught
the mismatch: the test looked like it pinned a public contract and did not.

## What Didn't Work

Taking the review's literal suggestion - "assert the statuses using the briefing
collection returned by `chart show --json`" - would have meant ADDING a briefings
projection to that command. The same task's acceptance says that projection stays
*unchanged*, so satisfying the finding as written would have violated the criterion it
was raised under. A review finding that presupposes a surface is not authorization to
build the surface.

## Solution

Probe the real CLI first (`chart show --json` in a throwaway repo, keys dumped), then fix
the claim instead of the API: pin the statuses in the chart record `briefings[]` where
they actually live, state in a comment why that is the right artifact, keep
`chart show --json` pinned as an unchanged discriminator-free projection, and cross-check
the same facts from public command output that does report them (`reopen`'s
`staled_briefings`, the emission envelope's `status`). Declined portion explained in the
re-review message rather than silently ignored - reviewer converged to SHIP in one round.

## Prevention

- **Spec prose names surfaces loosely.** "X in `<command> --json`" is often shorthand for
  the persisted record. Dump the command's real keys before writing an assertion that
  claims to pin it - one throwaway-repo invocation settles it.
- **A test that reads artifact B while invoking command A is a lie by adjacency.** Either
  assert what A returns, or say in a comment why B is the authority.
- **Decline-with-evidence is a valid review outcome.** When the fix a finding asks for
  contradicts an acceptance criterion, state the contradiction in the re-review message;
  do not expand a public envelope to make a comment go away.

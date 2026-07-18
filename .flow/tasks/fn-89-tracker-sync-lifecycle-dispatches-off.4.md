---
satisfies: [R12]
---

## Description

Live interleave proof + dogfood measurements.

**Size:** S
**Files:** none (evidence-only; task evidence + optionally a decision-record memory entry)

1. On a linked spec, run one REAL comment-shaped touchpoint through the new path: background dispatch, host does real work meanwhile, notification join, `sync check` clean (no false MISSING, no duplicate retro-fire), terminal line parsed from the LAST line.
2. Record measurements in evidence: runner tokens for the comment op, host-context lines added (should be ~2: dispatch + outcome), wall-clock overlap.
3. If any invariant wobbles (double retro-fire, unparseable line), STOP and file the finding - do not paper over.

## Acceptance
- [ ] R12: proof recorded with measurements; both MUST invariants held

## Done summary
Live interleave proof executed on linked FLOW-32 (R12). A real background tracker-runner (sonnet, working-tree agent contract, DISPATCH=forked) ran one comment-shaped work.done op while the host ran the full unittest suite in the foreground.

Measurements: runner 105.9s wall / ~124k tokens / 14 tool uses, ALL absorbed off-host; host suite 8m44s green in parallel (runner window 100% inside it - zero wall-clock added); host context grew by exactly 2 items (dispatch + join notification); terminal line parsed cleanly from the LAST line (TRACKER_RUNNER=updated). MUST invariants held: (1) single state-writer - runner wrote only its receipt + comment, spec sync-state (lastSyncedAt) untouched; (2) join-before-audit - sync check ran post-join, missing=[], no false MISSING, no duplicate retro-fire.

FINDING (filed per task rule, not papered over): the runner double-posted - 3 identical comments in 24s. Root cause: first mutation used shell-interpolated body, response parse failed (the documented linear-graphql escaping trap), runner retried twice with the file+variables pattern WITHOUT re-running the marker dedup check between attempts; the writes had all landed. Dedup protects across runs, not within-run blind retries. Fix shipped: retry rule in comments-sync.md (re-check marker before ANY re-post), mirror regenerated idempotent, commit 1ab812cc. Duplicates deleted from FLOW-32 (1 proof comment remains). Secondary observation for dogfood watch: runner mimicked the visible flow:lifecycle marker shorthand from earlier hand-posted comments instead of the canonical flow-next:sync marker; dedup still keyed correctly.
## Evidence
- Commits: 1ab812cc
- Tests: flowctl sync check fn-89 --events work.firstClaim,work.done -> missing=[] (post-join), python3 -m unittest discover (full suite, exit 0, overlapped with runner), live runner dispatch: TRACKER_RUNNER=updated parsed from LAST line, 105.9s, ~124k tok off-host
- PRs:
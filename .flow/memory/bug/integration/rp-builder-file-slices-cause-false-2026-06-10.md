---
title: RP builder file slices cause false-positive 'missing docs' review findings
date: "2026-06-10"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-impl-review
tags: [rp, impl-review, builder-slices, false-positive, select-get, review-feedback]
problem_type: integration
symptoms: Reviewer flags a docs row as missing; the row exists outside the builder's line-slice of the file
root_cause: "RP builder slices large files for token budget; reviewer only sees the slice, not the full committed file"
resolution_type: fix
---

## Problem
RP impl-review on fn-58.4 (final-integration docs/release task, merge-base scope) returned NEEDS_WORK with a single P2/confidence-75 finding: "flowctl.md omits the new `tracker.readyState` config row". The row existed in the committed diff at flowctl.md:562 — the RP builder had sliced the file to lines 520-555 for token budget, cutting the `Available settings` table mid-way, so the reviewer literally could not see the row seven lines below its slice boundary.

## What Didn't Work
`flowctl rp select-add` cannot force a full-file selection over a builder slice (no `--full` flag) — re-adding the path left the 520-555 slice in place.

## Solution
Diagnose BEFORE fixing: `flowctl rp select-get --window W --tab T` shows each file's slice ranges. The finding's target line (562) fell outside the slice (520-555) → false positive. Resolution: same-chat re-review message quoting the missing region VERBATIM as evidence (the row text + its position after the `conflictTiebreak` row), explicitly stating no code change was made and why. Reviewer confirmed slice artifact and issued SHIP.

## Prevention
When an RP reviewer flags something as MISSING from a file you know you edited, check `rp select-get` slice ranges first — if the flagged location is outside the slice, do NOT "fix" it (you would duplicate the row/section). Quote the absent region verbatim in the same-chat re-review instead. Large reference docs (flowctl.md ~1400 lines) are the highest-risk files for mid-table slice cuts.

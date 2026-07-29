---
title: Caller oracle must preserve historical quirks and exact observations
date: "2026-07-29"
track: bug
category: integration
module: plugins/flow-next/tests/test_tracker_caller_oracle.py
tags: [fn-141, tracker-sync, oracle, impl-review]
problem_type: integration
symptoms: Oracle self-consistency tests passed while historical event tags and stream evidence were wrong
root_cause: Fixture normalized future behavior and stored prose instead of source-backed inactive and active observations
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/ceremony-validation-must-read-persisted-2026-06-28, bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
The first caller oracle normalized desired future event tags into the historical baseline and stored active observations as prose. Review showed that interview and plan did not emit event tags at the pinned commit, and prose streams could not support the later byte comparison.

## What Didn't Work
Shape-only tests proved that every field existed, but not that the field values matched the pinned caller sources or were comparison-ready.

## Solution
Record historical differences rather than normalizing them: interview and plan have untagged receipts and no event argument. Split config reads into inactive and active observations, and scope stdout/stderr to byte-exact tracker-touchpoint deltas. Add assertions against the pinned source commit.

## Prevention
An oracle test must validate independent source evidence, not only fixture self-consistency. Any future fake-flowctl comparison needs exact scenario-specific values, explicit dynamic-value normalization, and separate inactive/active observations.

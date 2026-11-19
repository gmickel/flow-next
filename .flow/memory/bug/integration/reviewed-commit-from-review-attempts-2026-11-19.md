---
title: "Reviewed commit from review_attempts: skip superseded, require observed head"
date: "2026-11-19"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [review-provenance, head-sha, plan-review]
problem_type: integration
symptoms: Drift check read a superseded or finalize-time head_sha as the reviewed commit
root_cause: Last plan row may be superseded; head_sha_observed false is finalize-time; plan reservations stored no head
resolution_type: fix
related_to: [bug/integration/a-new-terminal-status-needs-every-2026-10-05, bug/integration/bundled-snapshot-pr-listing-truncation-2026-09-26, bug/integration/dispatch-settings-must-reach-the-2026-10-17, bug/integration/review-backend-adapters-move-2026-10-05]
---

## Problem
Code that reads "the commit a review saw" from a spec's `review_attempts` took the last plan row's `head_sha`. Review showed three ways that is wrong: a late reservation finalizes after a fresh SHIP and is appended last as superseded evidence; a row with `head_sha_observed: false` holds finalize-time HEAD, which can postdate the review; and host plan reviews reserved with no range, so every host verdict fell back to finalize-time HEAD.

## What Didn't Work
Taking `rows[-1]["head_sha"]` for the latest `kind == "plan"` verdict. Ignoring the observed marker made a change committed during a host review look reviewed. Honouring the marker alone made host reviews never qualify.

## Solution
Select the latest plan verdict row without `superseded_by`, and accept its `head_sha` only when `head_sha_observed is True` (`plan_review_drift` in flowctl.py). Plan reservations without a range now store HEAD at reserve time (`enforce_and_increment_review_cap`), which the recorder promotes to an observed reviewed commit, so host reviews carry one too.

## Prevention
Any reader of review provenance tests three fixtures: a late superseded row appended after a SHIP, a `head_sha_observed: false` row, and a host-style record that passes no reviewed commit with a change committed between reservation and verdict.

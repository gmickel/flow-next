---
title: A started tracker state normalizes to in_progress or in_review by name
date: "2026-11-19"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl_tracker/status/policy.py
tags: [tracker, status-policy, linear, jira]
problem_type: integration
symptoms: status rule for started states misses a state named '...review'
root_cause: _norm_linear/_norm_jira map a started state with 'review' in its name to in_review
resolution_type: fix
related_to: [bug/integration/a-new-create-input-must-reach-the-2026-11-16, bug/integration/a-new-terminal-status-needs-every-2026-10-05]
---

## Problem
A status-policy rule meant for "a card in a started-type tracker state" listed only `in_progress` as the tracker slot. Linear (`started` type) and Jira (In Progress category) normalize a started state whose name contains "review" to `in_review`, so a configured ready state named "Ready for Review" still hit `status conflict (unmapped)`.

## What Didn't Work
Testing only one started-state name ("Queue"). It normalizes to `in_progress` on every provider and hides the name-based split.

## Solution
The ready-state agreement in `flowctl_tracker/status/policy.py` `decide()` accepts `tracker_norm in EARLY | {in_progress, in_review}`, and the facade tests add a review-named ready state for Linear and Jira.

## Prevention
When a rule targets "started" tracker states, cover both slots a started state can normalize to (`_norm_linear` / `_norm_jira` in `status/providers.py`), with one fixture whose name contains "review".

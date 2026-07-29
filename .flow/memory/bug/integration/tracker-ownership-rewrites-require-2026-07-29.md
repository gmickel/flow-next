---
title: Tracker ownership rewrites require adjacent fidelity sweeps
date: "2026-07-29"
track: bug
category: integration
module: plugins/flow-next/docs/tracker-sync.md
tags: [fn-141, tracker-sync, docs-contract, provider-fidelity, impl-review]
problem_type: integration
symptoms: "Review found stale route, Jira version, and GitHub relation claims after the primary ownership rewrite"
root_cause: Only primary ownership sections were rewritten; adjacent discovery and provider-fidelity claims were not cross-checked against implementation
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/caller-facade-guards-must-cover-retro-2026-07-29, bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29, bug/integration/caller-oracle-must-preserve-historical-2026-07-29, bug/integration/ceremony-validation-must-read-persisted-2026-06-28, bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem

The deterministic tracker ownership rewrite passed focused tests but review found
stale adjacent contracts. Recovery prose still described runtime route selection,
Jira discovery still allowed an unsupported alternate API version, and the shared
dependency section described GitHub as using a fenced body block even though the
implementation projects a `sub_issues` hierarchy proxy with structured degradation.

## What Didn't Work

Editing only the primary ownership and command-reference sections. Tracker behavior
was also restated in lifecycle recovery, discovery steps, dependency direction,
idempotency, provenance, and body-merge prose.

## Solution

Sweep every adjacent semantic claim after an ownership reversal. Cross-check
provider fidelity against `flowctl_tracker/relate/providers.py` and its contract
tests, not against the retired skill prose. Document Jira version 2 as mandatory
resolver and migration output, and document GitHub `sub_issues` as hierarchy
degradation rather than blocked-by.

## Prevention

For tracker documentation changes, search the whole skill and docs tree for old
route vocabulary, then inspect each provider-fidelity bullet independently.
Run mirror parity, prompt pins, and the relevant provider contract tests before
review. Recompute always-loaded prompt weight whenever an always-read file changes.

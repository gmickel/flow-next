---
title: Caller fakes must enforce lifecycle facade input contracts
date: "2026-07-29"
track: bug
category: integration
module: plugins/flow-next/tests/test_tracker_caller_execution.py
tags: [fn-141, tracker-sync, caller-harness, facade, impl-review]
problem_type: integration
symptoms: End-to-end caller tests passed with incomplete facade argv and vacuous streams
root_cause: The fake logged argv but did not enforce production input or output contracts
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/caller-facade-guards-must-cover-retro-2026-07-29, bug/integration/caller-oracle-must-preserve-historical-2026-07-29, bug/integration/ceremony-validation-must-read-persisted-2026-06-28, bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
The tracker caller execution harness accepted incomplete lifecycle facade calls and returned no output, so active-path tests could pass while omitting required operation inputs or ignoring a JSON stream leak.

## What Didn't Work
The first fake only logged tracker sync argv. It did not validate the real push, pull, reconcile, and comment file contracts, and its empty success response made stdout preservation vacuous.

## Solution
The fake now enforces the production operation-to-input matrix, verifies every supplied file exists, and emits realistic success JSON. The instrumented wrapper supplies complete input files and captures the JSON, so caller stdout and stderr remain unchanged.

## Prevention
Executable caller fakes should reject any request the production parser or facade rejects. Model the success envelope too, then assert the wrapper consumes it without changing caller streams.

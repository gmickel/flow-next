---
title: set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)
date: "2026-06-03"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-52, tracker-sync, github, identifier, validator, smoke-test]
problem_type: integration
symptoms: sync set-tracker-id --identifier '#1' rejected; GitHub adapter cannot store a link
root_cause: "validate_tracker_identifier only accepts Linear handle form; GitHub #N is display-only, not a resolvable handle"
resolution_type: fix
related_to: [bug/integration/drop-receipt-to-break-codex-2026-05-09, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
`flowctl sync set-tracker-id` rejected a GitHub issue identifier `#1` (caught live during the fn-52 GitHub round-trip smoke): "Invalid tracker identifier '#1'. Expected a bare display key like WOR-17". The strict `validate_tracker_identifier` only accepts the Linear handle form (`key-number`, e.g. WOR-17) because that form must be a RESOLVABLE bare handle for the R16 hybrid id scheme. But a GitHub identifier is `#N` (a display reference used in a `Refs #N` PR cross-link), NOT a resolvable spec handle — so the GitHub adapter could never store a link, and make-pr's §4.6a `Refs #N` linkage would have no id.

## Solution
Added `allow_reference=True` to `validate_tracker_identifier`: when set, it also accepts a GitHub-style reference (`#123` or `owner/repo#123`) and returns `("", number, display)` — empty key signals DISPLAY-ONLY (stored + shown + used in `Refs #N`, but NOT indexed as a resolvable handle). `cmd_sync_set_tracker_id` passes `allow_reference=True` (link time, any tracker). `cmd_spec_create --tracker-first` does NOT pass it, so a GitHub `#N` can never become a canonical spec id (verified: `spec create --tracker-first --tracker-identifier "#2"` still rejects). Regression tests in test_tracker_sync_state.py (`#42` + `owner/repo#7` accepted; `#abc` + `wor-17-slug` rejected; Linear `WOR-17` still strict).

## Prevention
When a validator enforces "must be a resolvable handle", check whether every tracker that flows through it actually has resolvable handles. Linear keys resolve (`work wor-17`); GitHub/Jira `#N` references do not — they are display-only. A multi-tracker identifier validator needs a display-only acceptance path, gated so only the resolvable-handle callers (canonical-id generation) stay strict.

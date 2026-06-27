---
title: "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus"
date: "2026-06-27"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
tags: [fn-68, tracker-sync, adapter-interface, marker, comments-sync, listComments, question-valve, nine-method, cross-model-review]
problem_type: integration
symptoms: comments-sync said flow-next:question is flow-owned (skip Sync Log) but the adapter comment.marker contract still detected only flow-evt:<event> — an adapter would return marker:null and wrongly import the parked question into the Sync Log
root_cause: documented new marker behavior only in the consumer file (comments-sync.md) while leaving the producer contract (comment.marker field + each adapter's listComments) describing the old marker set
resolution_type: fix
related_to: [bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
fn-68.2 added the `flow-next:question` / `flow-next:answer` async question-valve markers to tracker-sync's comment channel, and stated in `comments-sync.md` that a parked `flow-next:question` is flow-owned (so it is NOT imported into the spec `## Sync Log`). But the normalized-`comment.marker` contract in `adapter-interface.md` and all three `listComments` adapter docs (`github.md`, `linear-graphql.md`, `linear-mcp.md`) still told adapters to set `marker` ONLY from the `flow-evt:<event>` lifecycle token. An adapter faithfully following the adapter docs would return a parked question with `marker: null`, and comments-sync's pull-dedup would treat it as a genuine tracker comment and append it to the Sync Log — directly contradicting the new prose.

Same class, separately: adding the 9th adapter method (`listOpenIssues`) left stale "six-method" / "eight-method transport interface" + "The six interface methods over X" headings/prose across the per-transport adapter docs, internally split-brained against the now-nine-method `adapter-interface.md`.

## What Didn't Work
Documenting the new marker behavior ONLY in the consumer file (`comments-sync.md`) while leaving the producer contract (the `comment.marker` field doc + each adapter's `listComments`) describing the OLD marker set. Cross-model review (RepoPrompt) caught it as a contract gap an agent could implement wrong.

## Solution
Make the flow-owned marker set a CLOSED, explicitly-tabulated vocabulary in the producer contract: `adapter-interface.md` § `comment` gained a marker-vocabulary table — `flow-next:sync`→`flow-evt:<event>`, `flow-next:question`→`flow-evt:question`, rolling `flow-next:status`→`flow-evt:status` (all flow-owned, skip Sync-Log); `flow-next:answer`→`marker:null` (the ONE human-authored marker) but the adapter surfaces its `id` and the answer round-trip claims it by `id` BEFORE the generic Sync-Log append (unmatched answers fall through to a real comment). All three `listComments` docs + the comments-sync pull-dedup flow were updated to detect the closed set. For the method-count: relabeled every per-transport doc to "nine-method" / "original six core methods" with explicit scoping notes.

## Prevention
When a sync/projection feature adds a marker or struct-field semantics, update the PRODUCER contract (the normalized struct field + every adapter that emits it), not just the consumer/reconcile doc — the two drift silently and an adapter author implements the stale side. A prose-contract test should assert the closed vocabulary is named in BOTH the interface contract and each adapter's read path. For interface-method additions, grep the whole skill tree for stale "<N>-method" / "the <count> interface methods" wording and add a test guard forbidding the old count across all adapter docs (allow only explicitly-scoped "original six core" subset references).

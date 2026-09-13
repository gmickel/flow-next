---
title: "Land chain fences: a failed read is never permission; write multi-layer records "
date: "2026-09-13"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-land/workflow.md
tags: [fn-149, land, chains, stacks, cascade, skill-prose, codex-review, review-feedback]
problem_type: runtime-error
symptoms: "Round-1 codex found 9 defects: failed child/parent reads enabled delete/standalone, binding reused as merge-verdict green, partial cascade record writes, one-directional reset guard"
root_cause: cmd || VAR=default treated an unread as an empty read; gate evidence carried across gates; per-layer ledger writes and one-way containment checks
resolution_type: fix
---

## Problem
fn-149.1 added chain/stack landing to the land skill as prose fences. Codex found nine round-1 defects that shared one shape: a failed or partial read became permission. `|| CHILD_COUNT=0` on a failed child list re-enabled `--delete-branch` (the exact child-closing failure the change prevents); an empty parent walk after a failed `gh pr list --head` classified a chain layer as standalone; `|| KIDS='[]'` in cascade discovery truncated the chain and published a lower rewrite alone; a review-evidence binding was reused as a green merge-verdict command result; per-layer ledger writes during cascade reconcile left a fresh lower tip beside a stale upper one after an interruption; a scoped-handoff `reset --hard` guard that checked only remote-subset-of-local could drop an unpushed local commit; a per-commit reverse-apply check refused a valid rewrite when the squash-merged parent edited one file twice.

## What Didn't Work
Defaulting a failed read to the "nothing there" value and moving on; carrying a gate result from evidence that never recorded that gate; persisting a multi-layer rewrite one layer at a time; checking containment in one direction only.

## Solution
Failed reads become a distinct `unknown`/`read_failed` state that holds the merge or keeps the branch (workflow.md §2.0, §2.8, §3.5); the merge-verdict command re-runs at the current head like CI and the binding carries review evidence only (§2.2b, §2.9); cascade reconcile accumulates replacements in memory and rewrites the record once after every layer succeeds (references/chains-and-stacks.md); the handoff reconcile checks both directions and unwinds local-only commits newest-first on one scratch index seeded from the base tree (references/flow-handoff.md). Each has an executable fixture in tests/test_land_chain_fixtures.py with a stub gh failure mode.

## Prevention
For every `cmd || VAR=<default>` in a skill fence, ask whether the default is a permission (delete, merge, classify standalone, clear a record); if so the failure needs its own state and a hold. For every multi-step record update, write once after the last step or make each partial state self-consistent. For every guard before a destructive git command, test both containment directions and add a fixture with an unpushed local commit.

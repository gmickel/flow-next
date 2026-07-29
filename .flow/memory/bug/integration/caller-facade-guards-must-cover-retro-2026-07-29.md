---
title: Caller facade guards must cover retro-fire paths
date: "2026-07-29"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-capture/workflow.md
tags: [fn-141, tracker-sync, facade, retro-fire, oracle]
problem_type: integration
symptoms: Primary facade path passed while Capture retro-fire retained legacy lifecycle grammar
root_cause: Whole-file positive assertion did not distinguish multiple lifecycle callsites
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/caller-oracle-must-preserve-historical-2026-07-29, bug/integration/ceremony-validation-must-read-persisted-2026-06-28, bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
The primary Capture lifecycle touchpoint used the fn-140 facade, but its bounded MISSING-receipt retro-fire still instructed the removed skill-dispatch grammar.

## What Didn't Work
The current-tree oracle checked that each whole caller file contained a facade command. A primary call satisfied that assertion even when a second lifecycle callsite in the same file remained stale.

## Solution
Rewire the retro-fire to re-resolve the full perEvent mapping, re-synthesize caller-owned comment content, and invoke the inline wrapper for exactly one facade call. Add a negative oracle assertion rejecting legacy lifecycle grammar that combines `skill: flow-next-tracker-sync` with an event tag.

## Prevention
When replacing lifecycle dispatch machinery, enumerate primary, retry, retro-fire, and audit paths separately. Pair positive facade assertions with a negative legacy-grammar assertion across the explicit caller inventory.

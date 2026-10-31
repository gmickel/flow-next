---
title: "Trimming skill-fence calls drops failure paths: malformed probes, read <<< $(cmd"
date: "2026-10-31"
track: bug
category: runtime-errors
module: plugins/flow-next/skills
tags: [skill-fences, shell, snapshot, refactor]
problem_type: runtime-error
symptoms: a removed or merged call loses its fallback or exit status on bad input
root_cause: only the healthy path was checked; read here-strings hide the substituted command's status
resolution_type: fix
---

## Problem
A wave that removed redundant calls from skill fences passed a full suite yet drew three review
findings, each a lost failure path rather than a wrong happy path. A snapshot probe with status
`ok` but a null value skipped the live fallback. `read -r A B <<< "$(gh ...)"` swallowed a failed
`gh` exit status, so the fence went on to `git push "" "HEAD:"`. And dropping "Step 1" from four
completion-review workflows left lowercase "Re-run step 2" lines pointing at verdict handling.

## What Didn't Work
Checking only the healthy path and the status-error path. A case-sensitive `grep "Step [0-9]"`
for references before renumbering.

## Solution
Accept a snapshot value only when it has the expected shape (`(.value.total_terms | type) ==
"number"`), else fall back to the live call. Capture command output in a standalone assignment
with `|| exit 1`, then split it with `read`. Renumbered steps: `grep -in "step [0-9]"` across the
skill directory.

## Prevention
When replacing a call with a cached value or merging two calls, test the failed and malformed
inputs as well as the healthy one: a stub that fails and a payload with the wrong shape.

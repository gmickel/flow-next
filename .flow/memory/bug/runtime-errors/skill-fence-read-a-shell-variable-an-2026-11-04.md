---
title: Skill fence read a shell variable an earlier tool call set; persisted file ignor
date: "2026-11-04"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-flow/auto.md
tags: [skill-fence, shell-state, flow-auto, test-masking]
problem_type: runtime-error
symptoms: Off-GitHub make-pr verify reported a probe failure after a successful snapshot refresh
root_cause: Fence read $PILOT_SNAPSHOT without reloading .flow/tmp/pilot-snapshot.json; the test preset the variable
resolution_type: fix
---

## Problem
A new `flow --auto` fence (the make-pr verify on a forge other than GitHub) read `$PILOT_SNAPSHOT` directly. Shell variables do not survive between tool calls, so a verify run in its own call parsed an empty string and reported `PR_VERIFY_FAILED=1`, a false probe failure, even though the refreshed snapshot held the open merge request.

## What Didn't Work
The first test fed the fence's single `OPEN_PR_URL=` line with `PILOT_SNAPSHOT` preset in the same shell, which hid the cross-call case.

## Solution
The fence starts with the same reload line every other snapshot consumer in auto.md uses: `[ -n "${PILOT_SNAPSHOT:-}" ] || PILOT_SNAPSHOT="$(cat "$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json" 2>/dev/null)"`. The test now runs the whole fence in a fresh shell, with `PILOT_SNAPSHOT` removed from the environment, in a temporary repo holding the persisted file.

## Prevention
A skill fence that reads state produced by an earlier fence reloads it from its persisted file first. Test such fences in a fresh shell with the variable unset, never with the variable preset.

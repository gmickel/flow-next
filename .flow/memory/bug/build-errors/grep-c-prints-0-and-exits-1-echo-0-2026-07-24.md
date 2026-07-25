---
title: "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count"
date: "2026-07-24"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-audit/workflow.md
tags: [bash, skill-prose, grep, shell-pitfall]
problem_type: build-error
symptoms: numeric comparison fails with an arithmetic syntax error on the zero-match path
root_cause: "grep -c emits the count then exits 1 on no match, so a || echo 0 fallback appends a second zero"
resolution_type: fix
related_to: [bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10]
---

## Problem
Skill prose (and any bash we ship) that counts matches with `grep -c '<pat>' <file> 2>/dev/null || echo 0` is broken on the ZERO-match path — the most common path. `grep -c` **prints `0` AND exits 1** when nothing matches, so the `|| echo 0` fallback fires and appends a SECOND zero. The captured variable becomes the two-line string `"0\n0"`, and the next `[[ $VAR -ge 2 ]]` blows up with an arithmetic syntax error.

Surfaced by codex impl-review on fn-122.2 (audit Harden pre-scan), Major/confidence-100.

## What Didn't Work
The `|| echo 0` idiom reads as defensive and is copied widely from `grep -q` / plain `grep` usage, where a non-zero exit really does mean "no output". It is wrong specifically for `-c` (and `-l` with `-c`-like reasoning), because the count is already printed before the exit status is set.

## Solution
Swallow the exit status instead of substituting a value, then default only if genuinely empty:

```bash
COUNT=$(grep -c '^## Update ' "$file" 2>/dev/null || true)
COUNT=${COUNT:-0}
```

Landed in `plugins/flow-next/skills/flow-next-audit/workflow.md` §0.75.1.

## Prevention
- Reviewing any shipped bash snippet: check whether the command PRINTS its result before exiting non-zero. `grep -c`, `grep -o | wc -l`, and `git log ... | wc -l` all print first — `|| echo N` corrupts them; `|| true` plus a `${VAR:-N}` default is the safe shape.
- Skill prose is executed verbatim by host agents, so a broken snippet is a runtime bug, not a doc typo. Review bash in prose with the same rigor as bash in scripts.

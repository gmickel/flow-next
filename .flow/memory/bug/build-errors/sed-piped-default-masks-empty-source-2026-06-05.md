---
title: "sed-piped default masks empty source: || fallback never fires"
date: "2026-06-05"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-qa/workflow.md
tags: [fn-53, skill-bash, base-ref-detection, branch-match, sed-exit-code, make-pr-pattern, codex-review]
problem_type: build-error
symptoms: DEFAULT_BRANCH/BASE_REF ends up empty when origin/HEAD unset; export-cognitive-aid --base then fails
root_cause: cmd | sed ... || echo default — sed exits 0 on empty input so the || default is unreachable; and literal branch==spec-id match misses flow branches
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26]
---

## Problem
A skill's base-ref detection used `git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || echo main`. The `|| echo main` fallback NEVER fires when `origin/HEAD` is unset, because `sed` consumes the empty stdin and exits 0 — so the `||` branch is unreachable and `DEFAULT_BRANCH` ends up empty. The downstream `git merge-base "$DEFAULT_BRANCH" HEAD` then fails, breaking `spec export-cognitive-aid --base`. Separately, branch→spec resolution matched the literal branch name against the spec id (`flowctl show "$BRANCH"`), which only works when the branch name equals the spec id — flow branch names need not.

## What Didn't Work
Trusting a `cmd | sed ... || fallback` idiom for defaulting: the exit code reflects the LAST pipeline stage (`sed`), not whether the source command produced output. The `||` only fires on `sed` failure, not on empty input.

## Solution
Reuse the make-pr proven patterns (flow-next-make-pr/workflow.md §0.2-§0.3):
- Base: a `for candidate in origin/main main origin/master master` loop gated on `git rev-parse --verify --quiet`, hard-erroring when none resolve, then `merge-base` for a stable diff base (`workflow.md` §1.2).
- Branch-match: scan `.flow/specs/*.json` + `.flow/epics/*.json` `branch_name` via jq instead of literal `branch == spec-id` equality (`workflow.md` §1.1).

## Prevention
When defaulting from a command's output, branch on the captured value (`[[ -z "$X" ]]`), never on a `cmd | sed | tr ... || echo default` exit code — the trailing filter masks the source's success/failure. For base-ref / branch→spec resolution in any new flow-next skill, copy the make-pr cascade rather than re-deriving a one-liner.

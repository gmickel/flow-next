---
title: Final-gate grep for a forbidden token hits the prohibition prose that bans it
date: "2026-07-02"
track: bug
category: test-failures
module: plugins/flow-next/skills/flow-next-impl-review
tags: [acceptance-gates, grep, spec-authoring, fn-81, review-feedback]
problem_type: test-failure
symptoms: fn-81.4 gate grep for 'git add -A' could never be empty; NEEDS_WORK at confidence 100
root_cause: "Same spec required removing a token AND adding prohibition prose naming that token, then grepped for the literal"
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
related_to: [bug/test-failures/test-production-path-not-parallel-construction-2026-05-21]
---

## Problem
fn-81.4's acceptance criterion required `grep -rn 'git add -A' <two review-skill dirs>` to be EMPTY, but fn-81.2 (a dependency of the same spec) had deliberately added prohibition prose containing that exact literal ("NEVER `git add -A`", anti-pattern bullets) to those same dirs. The gate grep could never pass — impl-review returned NEEDS_WORK (confidence 100) on the contradiction.

## What Didn't Work
Treating the hits as "clean by intent" (prohibitions, not instructions) and documenting them — the reviewer correctly held the literal acceptance text as the contract.

## Solution
Reworded the prohibition sites to name the long-form flag instead ("never blanket-stage with `git add --all`"). Those prohibitions now live in `skills/flow-next-impl-review/references/fix-loop.md` and `skills/flow-next-spec-completion-review/workflow-common.md`. The guard stays concrete; the grep token is gone.

## Prevention
When a spec pairs "remove usage of X" (one task) with "final-gate grep for literal X must be empty" (another task), the prohibition prose that REPLACES the usage will itself contain X. At planning time either scope the gate grep to executable contexts (e.g. exclude negative-guard lines) or mandate long-form/paraphrase in the prohibition wording. Prohibitions that name `git add -A` itself still exist in the work, resolve-pr, audit, features, qa and worktree-kit skills, so a gate grep for the literal must be scoped to the files the gate is about.

---
title: Final-gate grep for a forbidden token hits the prohibition prose that bans it
date: "2026-07-02"
track: bug
category: test-failures
module: plugins/flow-next/skills/flow-next-impl-review
tags: [acceptance-gates, grep, spec-authoring, fn-81, review-feedback, rp-slices]
problem_type: test-failure
symptoms: fn-81.4 gate grep for 'git add -A' could never be empty; NEEDS_WORK at confidence 100
root_cause: "Same spec required removing a token AND adding prohibition prose naming that token, then grepped for the literal"
resolution_type: fix
related_to: [bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09, bug/test-failures/test-production-path-not-parallel-construction-2026-05-21]
---

## Problem
fn-81.4's acceptance criterion required `grep -rn 'git add -A' <two review-skill dirs>` to be EMPTY, but fn-81.2 (a dependency of the same spec) had deliberately added prohibition prose containing that exact literal ("NEVER `git add -A`", anti-pattern bullets) to those same dirs. The gate grep could never pass — impl-review returned NEEDS_WORK (confidence 100) on the contradiction.

## What Didn't Work
Treating the hits as "clean by intent" (prohibitions, not instructions) and documenting them — the reviewer correctly held the literal acceptance text as the contract.

## Solution
Reworded the 6 prohibition sites to name the long-form flag instead: "never blanket-stage with `git add --all`" / "Blanket staging (`git add --all`) in the fix loop" (impl-review SKILL.md:356, workflow-rp.md:364/428; spec-completion-review SKILL.md:183, workflow-rp.md:471/535). Guard stays concrete; grep token gone. Mirror regenerated (idempotent), commit 45586ef1.

## Prevention
When a spec pairs "remove usage of X" (one task) with "final-gate grep for literal X must be empty" (another task), the prohibition prose that REPLACES the usage will itself contain X. At planning time either scope the gate grep to executable contexts (e.g. exclude negative-guard lines) or mandate long-form/paraphrase in the prohibition wording. Secondary lesson: RP line-range selection slices go stale after commits shift lines — a reviewer citing "missing content at :N" in a sliced file may be looking at drifted windows; re-attach the FULL file and rebut with fresh grep line numbers.

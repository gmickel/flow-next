---
title: Retiring a value flag leaks its value; emitter switches need semantic fixtures
date: "2026-10-31"
track: bug
category: integration
module: plugins/flow-next/skills
tags: [flags, prime, emitter, review]
problem_type: integration
symptoms: a retired flag's value becomes the target; an emitter agrees on verdicts but not on rule semantics
root_cause: "split-form value not consumed; comparison checked verdicts, not the rule's scoping"
resolution_type: fix
related_to: [bug/integration/review-backend-adapters-move-2026-10-05]
---

## Problem
Two review findings on the audit's wave 3. Removing the split-form `--research <value>` case from
`flow --auto`'s parser left the value to fall through as a positional argument, so
`--research grep fn-9` selected spec `grep`. Separately, switching prime's DE1 to the emitter rested
on a four-repo comparison that agreed on the verdict, while the emitter's semantics (declarations
pooled across members, docs sources counted) differed from the host rule and showed up on a
two-member fixture.

## What Didn't Work
Testing only the `--flag=value` spelling of the retired flag. Comparing emitter and host on
real repositories by verdict alone.

## Solution
Keep a retired value-taking flag in the parser only to warn and consume its value. Keep DE1 on the
host; the criterion map now names the host as owner for DE1 and DE4.

## Prevention
When retiring a flag that took a value, test the split spelling and a position before the
target. Before switching a check to an emitter, compare the rule's semantics on a fixture built
to separate them, not only the verdicts on whatever repositories are at hand.

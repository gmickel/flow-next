---
title: Scheduler prose asserted wrong config default; slot-hold drain rules deadlock
date: "2026-08-22"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md
tags: [fn-203, work-rolling, planSync, config-defaults, deadlock, skill-prose]
problem_type: integration
symptoms: Beta always degrades to serial on fresh repos; collision retry waits forever
root_cause: Gate prose assumed planSync default off (shipped default true); drain condition included the holder's own slot
resolution_type: fix
related_to: [bug/integration/byte-for-byte-spec-contract-branch-2026-07-01, bug/integration/skill-fence-consolidation-6-contract-2026-07-20]
---

## Problem
Review (fn-203.6, codex) caught two P1s in the rolling-scheduler beta prose:
(1) the plan-sync gate claimed `planSync.enabled` off "(null/false/missing - the default)",
but the SHIPPED default is `true` (`get_default_config()` in flowctl.py, and
`config get` answers the default when the key is absent) - so every fresh-repo
beta run would silently degrade to serial and never exercise the scheduler;
(2) join-collision recovery said "retry after the in-flight set drains" while
the lifecycle contract has the losing task keep its slot - a self-deadlock,
and the single-hold fix still deadlocked when a SECOND task collided during
the drain.

## What Didn't Work
Writing gate prose from the intuitive assumption that an opt-in feature's
config knob defaults off. Fixing the deadlock for one held task only ("drain
every other task") - two held tasks each wait on the other.

## Solution
(1) Stated the real default on every surface (scheduler gate, beta SKILL.md,
CHANGELOG, orchestration, troubleshooting) and made `planSync.enabled=false`
an explicit prerequisite: interactive runs offer the opt-out command once,
autonomous runs report and never mutate config.
(2) Ordered collision-retry queue: held tasks keep claim+slot, drain every
NON-HELD task, retry queued tasks one at a time (a parked hold never blocks
the active retry). rolling-scheduler.md ~3d.

## Prevention
Before writing prose that asserts a config key's default, read
`get_default_config()` in flowctl.py (or run `flowctl config get <key>` in a
fresh repo) - never assert a default from feature intuition. For any
hold-a-slot-and-wait rule, check the wait condition against the holder's own
slot AND against two simultaneous holders (deadlock needs only symmetry).

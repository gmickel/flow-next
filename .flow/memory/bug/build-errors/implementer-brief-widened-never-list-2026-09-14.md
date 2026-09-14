---
title: "Implementer brief widened never-list past the spec; child lost its fan-out"
date: "2026-09-14"
track: bug
category: build-errors
module: plugins/flow-next/templates/usage.md
tags: [fn-245, fn-244, bridge, long-task-brief, never-list, delegation, codex-review, review-feedback]
problem_type: build-error
symptoms: "Bridged child under the #436 brief could not spawn subagents; brief said never spawn another agent or bridge"
root_cause: "July 2026 keep-the-child-flat caveat (openai/codex#33267) promoted to policy; three checks read the brief as a restatement, not clause by clause"
resolution_type: fix
related_to: [bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26]
---

## Problem
PR #436 (fn-244) shipped the long-task brief for bridged implementers with the never clause "Never spawn another agent or bridge". The bridge safety rule it was derived from says "never spawns a bridge of its own"; no requirement in fn-244 asked for an agent-spawn ban. A bridged child under that brief could not fan out, so the direct route's premise (one owner sees the whole task and decides its own delegation) was broken for every project whose implementer tier is reached over a CLI bridge. Issue #431's reporter diagnosed the symptom in PR #437.

## What Didn't Work
Three checks let the clause through: the impl review read the brief as a whole and judged its tone, not each clause against the spec; the completion review judged R-IDs, and no R-ID named the never-list; the maintainer read the brief as a restatement of the safety rule it sat under. All three treated the July 2026 "keep the child prompt flat" caveats (openai/codex#33267) as standing policy rather than a dated workaround, so the wider clause read as consistent.

## Solution
fn-245: the brief's clause reads "never spawn another bridge" and the brief carries the judicious-subagent license (`plugins/flow-next/templates/usage.md`, long-task brief block); the worker's Phase 1b hands the task to the bridged child and passes the license through (`plugins/flow-next/agents/worker.md`); the July caveats became dated watch lines with the measured result (repro clean on codex-cli 0.153.4 with gpt-6-astra; zero decode errors across the September spawning runs) in `usage.md` and `docs/reach/codex.md`.

## Prevention
`.flow/criteria.md` G3: a never-list in an implementer brief, worker dispatch prose, or subagent license is diffed clause by clause against the spec that asked for it, and the owner (in-host worker or bridged child) is named explicitly. STRATEGY.md design principle "The owner holds the license" states the bound: safety rules cover push, history rewrite, scope, verdict, and a nested bridge, never the owner's own delegation. A caveat that traces to an upstream bug carries its date, version range, and issue number, so a later reader can re-measure instead of promoting it to policy.

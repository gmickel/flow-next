---
title: Forwarded license carried the wrong holder's commit contract into the bridged ch
date: "2026-09-14"
track: bug
category: integration
module: plugins/flow-next/agents/worker.md
tags: [fn-245, bridge, worker, phase-1b, license, dispatch-field, codex-review, review-feedback]
problem_type: integration
symptoms: Bridged child received single-commit-worker prose after a checkpoint brief; invocation implementer override unreachable from the worker; stage model read from self-report
root_cause: Verbatim pass-through of prose written for another holder; tier resolution moved into a fresh-context agent without checking which precedence inputs it can observe
resolution_type: fix
related_to: [bug/build-errors/implementer-brief-widened-never-list-2026-09-14, bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30]
---

## Problem
The first cut of the worker's bridged-implementer path (fn-245) forwarded the no-plan judicious-subagent paragraph to the bridged child verbatim. That paragraph said "the worker is the only committer; the single-commit convention stands", while the long-task brief above it told the same child to commit checkpoints per scope unit. Two more handoff gaps rode along: the fresh-context worker had no field for an invocation-level implementer override, so the routing precedence's highest rung was unreachable from inside the worker; and the stage line's `model:` field was to be read from the child's digest, which the brief never requested and which the reach page says is not evidence.

## What Didn't Work
Treating "pass the license through verbatim" as sufficient. Prose written for one holder (the in-host worker, single-commit convention) carried that holder's commit contract into a context with a different commit contract (the bridged child, checkpoint convention). Moving tier resolution into a fresh-context agent without checking which precedence inputs that agent can actually observe.

## Solution
`plugins/flow-next/skills/flow-next-work/references/no-plan-route.md`: the license names "the owner" as the only committer and defers the commit convention to the owner's path. `plugins/flow-next/skills/flow-next-work/phases.md` 3c and the SECTION3C heredoc in `scripts/sync-codex.sh`: optional `IMPLEMENTER: <model> at <effort>` dispatch line, consumed first by worker Phase 1b. `plugins/flow-next/agents/worker.md` Phase 1b: `model:` comes from the bridge command line the worker issued; only `delegated:` comes from the digest.

## Prevention
When prose is forwarded to a second holder, diff every clause that names an actor or a convention against the receiving context's contract (same discipline as G3's clause-by-clause never-list check). When a resolution step moves into a fresh-context agent, enumerate each precedence rung and confirm the agent can observe it; a rung it cannot see needs a dispatch field. A stage-line field needs a named producer that is evidence, never a self-report.

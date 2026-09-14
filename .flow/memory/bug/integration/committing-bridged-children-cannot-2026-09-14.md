---
title: Committing bridged children cannot share one checkout; inspect dirty tree before
date: "2026-09-14"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work/references/no-plan-route.md
tags: [fn-245, bridge, worker, parallel, git-index, codex-review]
problem_type: integration
symptoms: Parallel checkpointing children licensed in one checkout; on-return review skipped uncommitted remainder
root_cause: Shared-checkout subagent license reused for committing children; range review assumed a clean tree
resolution_type: fix
related_to: [bug/integration/spec-named-config-keys-must-be-checked-2026-07-15]
---

## Problem
The bridged-implementer prose in `no-plan-route.md` licensed "parallel bridge calls on disjoint surfaces, each with the same long-task brief" and then claimed "commit ownership and the join barrier stand unchanged". The long-task brief orders every child to `git add -A && git commit` checkpoints. Disjoint file surfaces in one checkout still share one Git index, so one child stages and commits another child's unfinished edits, and concurrent commits collide on `index.lock`. A join barrier before the worker's final commit cannot undo checkpoints taken mid-run. All three codex fan-out draws flagged it (P2, confidence 75-100). A second draw found that the worker's on-return inspection covered only `<base>..HEAD` while the explicitly supported sandbox-denied case leaves the whole implementation uncommitted beside that range.

## What Didn't Work
Reusing the shared-checkout subagent license (disjoint surfaces + join barrier) for children that checkpoint. That license was written for subagents that never commit; a committing child changes the invariant.

## Solution
`plugins/flow-next/skills/flow-next-work/references/no-plan-route.md` (Bridged implementer path paragraph): concurrent checkpointing children never share a checkout; each gets its own workspace and branch (the wave-worker isolation), its brief names that branch, and the worker integrates every returned branch onto the task branch after all children return; serial otherwise. `plugins/flow-next/agents/worker.md` (Bridged implementer, On return): `git status --porcelain` first; a dirty tree is committed under Phase 3's convention before the worker inspects `<base>..HEAD`, so the inspected range holds everything the child produced.

## Prevention
When prose grants a subagent or bridged child a `git add -A`/commit instruction, check every other rule in the same license against the shared-index assumption: "disjoint files" is not isolation for a committer. When a review step inspects a commit range, pair it with a dirty-tree check whenever a supported path (sandbox-denied commit) can leave work outside that range.

---
title: Final-integration tasks need wider impl-review base
date: "2026-05-26"
track: knowledge
category: workflow
module: review
tags: [fn-50, impl-review, review-scope, final-task, multi-task-spec, base-commit, merge-base, codex]
applies_when: Final-integration tasks need wider impl-review base
related_to: [knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30]
---

## Problem

Codex impl-review on a final-integration task (fn-50.6, the last of 6 tasks in an spec) was run with `--base $BASE_COMMIT` (= task-start commit, which already included tasks 1-5). The reviewer correctly saw the diff for THIS task, but had no visibility into whether the canonical files this task depended on (the skill scaffold, command shim, scout enrichments from fn-50.1 through fn-50.5) actually existed on the branch. It flagged a Major finding: "I do not see `plugins/flow-next/skills/flow-next-map/` or `plugins/flow-next/commands/flow-next/map.md` in the provided changed files."

That finding was a scoping artifact — the files exist on the branch, just not in the scoped diff. But the reviewer's tooling sees only the diff. So a perfectly correct integration task was flagged NEEDS_WORK twice on false-positive scoping grounds before I switched the base.

## What Didn't Work

Trying to "explain" the scope in commit messages or done summaries — the reviewer reads the DIFF, not the prose. Adding cross-references to prior commits doesn't help either.

## Solution

For **final-integration tasks** in a multi-task spec (release plumbing, cross-cutting wiring, anything that depends on N prior tasks landing), re-run impl-review with `--base $(git merge-base HEAD main)` instead of the task-start commit. This gives the reviewer the full feature-branch view so it can audit:

- Whether the canonical sources the mirror depends on actually exist
- Whether docs cross-references resolve to real files
- Whether the spec's R-IDs are all satisfied across the tasks

The wider scope IS more findings (the reviewer will surface latent bugs in prior tasks too — fn-50.6 review caught the `.clawpatch/.gitignore` directory-level bug from fn-50.1, the `set -e` swallowing `MAP_EXIT=$?` from fn-50.1, the `flowctl config get` text-mode false-none bug from fn-50.1, the prime DE7 detection missing FLOWCTL prelude from fn-50.5, and the sync-codex.sh agent generator missing rewrite — all of which were real and worth fixing before merge). But the false-positive "canonical files don't exist" finding goes away.

## Prevention

**Heuristic for picking impl-review base:**

| Task shape | Recommended base |
|---|---|
| Single-task spec (one PR, one task) | `merge-base` |
| Intermediate task in multi-task spec | Task-start commit (current default) |
| Final-integration task in multi-task spec | `merge-base` |
| Hotfix on main | HEAD~1 |

`/flow-next:impl-review` skill could detect "this is the last open task in the spec" and auto-widen to merge-base. Worth a future spec.

Until then: at task start, when claiming the FINAL task of a multi-task spec, capture `BASE_COMMIT=$(git merge-base HEAD main)` instead of `git rev-parse HEAD`.

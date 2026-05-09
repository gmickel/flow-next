---
title: codex impl-review false-positive on stale rename-scope task specs
date: "2026-05-09"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-impl-review
tags: [fn-43, rename, codex-review, scope-drift, false-positive, plan-sync, task-spec]
problem_type: build-error
symptoms: Codex review NEEDS_WORK on R12 scope-coverage; flagged files were already cleaned by upstream task
root_cause: Task spec scope-list named 4 files but T5 had pre-cleaned 2; reviewer can't grep outside diff to verify
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem

`/flow-next:impl-review` (codex backend) on rename-style epics flagged R12 NEEDS_WORK because the task spec listed 4 agent files but the diff only touched 2. The reviewer cannot grep files outside the diff to verify they're already clean — it reads the task spec's wording as the authoritative scope and emits a false-positive when prior tasks already cleaned some of the targets.

## What Didn't Work

- Re-running `flowctl codex impl-review` against the same diff via session resume — reviewer reproduces the same NEEDS_WORK because the diff is identical and the task spec wording is unchanged.
- Adding meta `<!-- Spec vocabulary verified clean -->` HTML comments to the agent files — pollutes canonical files with refactor breadcrumbs that have no business living there long-term. Reverted before commit.
- Trying to find subtle epic refs in the "already-clean" files via wider grep — confirmed zero remaining refs; nothing to change.

## Solution

Update the **task spec** (`.flow/tasks/<task-id>.md`) with plan-sync-style breadcrumbs noting which files in the original scope-list were already cleaned by earlier tasks (cite the commit hash). The task spec lands in the diff, and the reviewer sees the correction and reconciles. The breadcrumbs follow the same convention plan-sync writes (`<!-- Updated by plan-sync (T<N>): ... -->`), so the audit trail is consistent.

Specifically for fn-43.10:
1. Edited the Files / Approach / Investigation / Acceptance sections to add per-file breadcrumbs explaining T5's commit 225dc94 already cleaned `worker.md` + `quality-auditor.md`.
2. Touched the residual 1-ref low-density skills (`flow-next-audit/SKILL.md`, `flow-next-memory-migrate/SKILL.md`) since the reviewer flagged them as scope items even though they were just historical "this epic" prose.
3. Re-ran `flowctl codex impl-review` (session-resume via receipt) → SHIP.

## Prevention

For multi-task renames where some scope-listed files may be pre-cleaned by upstream tasks:

1. **Plan-sync should drift-correct task scope eagerly.** When T<N> finishes and any T<M>'s scope list (M > N) names files that T<N>'s commit just made canonical, plan-sync should write a `<!-- Updated by plan-sync (T<N> done): file already canonical via commit <hash> -->` breadcrumb on those line items. fn-43's plan-sync after T5 wrote a generic "T5 punted CLI verb rewrite to T10" breadcrumb but didn't enumerate per-file state — too coarse.

2. **Worker should grep-verify scope before declaring finding "out of scope".** When the impl-review flags a missing file the worker believes is already clean, the worker should: (a) grep the file to confirm zero remaining refs, (b) update the task spec breadcrumb to reflect reality, (c) re-run review with the corrected task spec in the diff.

3. **codex impl-review false-positives on rename scope are a recurring pattern.** Documented earlier in `bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08`. Pattern: codex reads spec wording as authoritative; cannot verify outside-diff state. Adding the file to the diff (even via task-spec-only edits) gives the reviewer something to reconcile against. Keep this in mind on every multi-task rename in the future.

---
title: Fence-preserving writer needs fence-aware readers/validators (write/read parity)
date: "2026-07-02"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-79, task-sections, fenced-code, markdown-parsing, cursor-review]
problem_type: data
symptoms: "Valid fenced '## ' content broke next set-acceptance (stale remnant, false duplicate) and validate"
root_cause: Normalization preserved fenced H2 lines but all downstream H2 scans of the file were fence-blind
resolution_type: fix
related_to: [bug/data/migrationrollback-cli-10-review-cycle-2026-05-08, bug/data/paired-snapshot-setter-must-write-both-2026-06-03]
---

## Problem
fn-79 added `normalize_section_content` which deliberately PRESERVES `## ` lines inside fenced code blocks when writing task-section content. Cursor impl-review (2 NEEDS_WORK rounds) caught that the downstream consumers of the persisted file were NOT fence-aware: `patch_task_section`'s duplicate-heading precheck + boundary splice, `get_task_section`, `validate_task_spec_headings`, and the `task set-spec --file` scaffold presence check all scanned with plain `line.startswith("## ")` / multiline regex. So valid content the new writer produced (e.g. a fenced `## Acceptance` example) broke the NEXT write (stale content left behind, false duplicate-heading error) or made `flowctl validate` reject a valid file.

## What Didn't Work
Fixing only the write-side normalization (round 1) — the invariant "fenced H2 is content, not a boundary" must hold at EVERY scan of the file, not just at the point that decides to preserve it.

## Solution
One shared fence tracker `_iter_fence_aware(lines)` (flowctl.py ~5147) yielding `(line, in_fence)`; every H2 scan of task `.md` content consumes it: `normalize_section_content`, `patch_task_section` (duplicate check + splice loop), `get_task_section`, `validate_task_spec_headings`, and `cmd_task_set_spec`'s missing-heading scaffold check. Regression tests in `tests/test_normalize_section_content.py` cover persisted fenced H2 idempotence, fenced byte-exact canonical heading (no duplicate error), fence-aware read, and validate parity.

## Prevention
When a writer starts intentionally persisting a shape (here: fenced `## ` lines inside sections), grep for every OTHER consumer that parses the same file for that token (`startswith("## ")`, `^## ` regexes) and give them the same awareness in the same change — write/read/validate parity is one invariant, not three features.

---
title: Section input computed outside anchor's fail-open capture boundary
date: "2026-09-26"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [anchor, fail-open, glossary, fn-258]
problem_type: runtime-error
symptoms: invalid UTF-8 task body aborts the whole flowctl anchor bundle
root_cause: glossary match text evaluated as an argument before _anchor_capture's try
resolution_type: fix
---

## Problem
fn-258 R1 filtered the anchor bundle's glossary section by the task's title and description. The match text was computed as an argument to `_anchor_capture(...)`, so it ran before the capture's exception boundary. A task Markdown file that was not valid UTF-8 then aborted the whole `flowctl anchor` bundle instead of marking one section unavailable. All three codex review draws reproduced it.

## What Didn't Work
Passing a pre-computed value into the capture call: `_anchor_capture(cmd_glossary_list, argparse.Namespace(match=_anchor_match_text(task_id)))`. Python evaluates the argument before the callee's `try`.

## Solution
Compute the section's input inside the captured callable: `_anchor_capture(lambda _ns: cmd_glossary_list(argparse.Namespace(json=True, match=_anchor_match_text(task_id))), None)` in `plugins/flow-next/scripts/flowctl.py` (`_anchor_sections`). `tests/test_anchor_bundle.py::UnreadableTaskBodyTest` writes non-UTF-8 bytes to the task body and asserts every section still renders.

## Prevention
In a fail-open assembler, any read a section depends on belongs inside that section's error boundary, including reads that only prepare an argument. When a section gains a new input, add an unreadable-input test for it.

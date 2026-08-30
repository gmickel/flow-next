---
title: "Delegating CLI wrapper inherits delegate guards, prints, truncation, races"
date: "2026-08-30"
track: bug
category: build-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-212, memory-upsert, delegation, codex-review, review-feedback, concurrency]
problem_type: build-error
symptoms: "upsert rejected cross-category matches, collapsed over-80 titles, raced on create, multi-line output"
root_cause: wrapper delegated to cmd_memory_add without re-checking the delegate's guards/normalization/prints/atomicity against its own contract
resolution_type: fix
---

## Problem
The first cut of `flowctl memory upsert` (fn-212) drew four review findings, all the same shape: a delegating wrapper inherits the delegate's assumptions unless each one is re-checked against the wrapper's own contract. Concretely: (1) delegation kept the caller's `--category`, so `cmd_memory_add`'s same-bucket guard rejected a legitimate cross-category title-within-track match; (2) truncating the lookup title to 80 chars to "match what add stores" silently collapsed distinct over-80 identities; (3) the scan and the delegated write were not covered by one lock, so concurrent zero-match upserts could both decide "create"; (4) the delegate's non-JSON progress prints leaked through, breaking the wrapper's one-line output contract.

## What Didn't Work
Treating "thin resolution layer over add" as "set args.update and call cmd_memory_add". The delegate's guard (bucket check), storage normalization (80-char truncation), print statements, and non-atomicity all became part of the wrapper's observable behavior.

## Solution
plugins/flow-next/scripts/flowctl.py `cmd_memory_upsert`: on a unique match, delegate with the matched entry's own category; reject over-80 titles with exit 2 instead of truncating; wrap scan + decision + write in `cross_process_lock(.flow/tmp/memory-upsert.lock)`; suppress the delegate's progress prints via an internal `_single_line` attr so exactly one Created/Updated line is emitted. Regression tests for each in tests/test_memory_upsert.py.

## Prevention
When wrapping an existing command function, enumerate the delegate's side contracts (guards, normalizations, prints, atomicity) against the wrapper's stated semantics before shipping - each mismatch is a finding waiting. A find-or-create verb needs one lock across find AND create.

---
title: Two independent resolve() calls faked a path escape on Windows
date: "2026-08-04"
track: bug
category: test-failures
module: plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py
tags: [windows, flake, path-safety, tracker, concurrency]
problem_type: test-failure
symptoms: "~50% windows-latest flake: legitimate .flow/create-first write refused with INVALID_INPUT '<leaf> escapes <base>'"
root_cause: "Non-strict Path.resolve() bails out early under concurrent writers, so base and leaf resolved independently could return two spellings (8.3 vs expanded) of the same directory"
resolution_type: fix
related_to: [bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04, bug/test-failures/windows-83-path-test-failures-were-2026-08-04]
---

## Problem
`leaf_is_safe` (`flowctl_tracker/lifecycle/helpers.py`) proved containment by
resolving base and leaf INDEPENDENTLY and comparing (`base_real not in
target_real.parents`). On `windows-latest` that produced a ~50% flake in
`test_tracker_capabilities.test_concurrent_relates_lose_no_ledger_entry`: a
legitimate write into `.flow/create-first/` was refused with `INVALID_INPUT`
"<leaf> escapes <base>" (run 30921678923 RED, identical re-run 30923544649
GREEN — the tell that it is nondeterminism, not logic).

Root cause: non-strict `Path.resolve()` on Windows is not deterministic under
concurrent writers. `ntpath._getfinalpathname_nonstrict` stops expanding on an
allowed winerror (SHARING_VIOLATION / ACCESS_DENIED) and returns the path
as-far-as-resolved. So one call could keep the 8.3 `RUNNER~1` spelling while
the sibling call expanded it — two spellings of the SAME directory comparing
unequal.

## What Didn't Work
Re-running CI (green) reads as "transient infra" and hides it. Any fix that
still calls `resolve()` twice keeps the race; so does comparing `os.path.realpath`
twice, for the same reason.

## Solution
Derive containment from ONE resolve. Keep a `base_dir.resolve()` only as the
unresolvable-path probe, then normalize the leaf LEXICALLY against the base with
`os.path.relpath(os.path.abspath(leaf), os.path.abspath(base))` and refuse when
`".." in Path(rel).parts`. `ValueError` (different Windows drive) is an escape.
The existing component-by-component no-follow symlink walk is what keeps a
symlink from redirecting the write, so lexical normalization loses no teeth.
See `plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py:40` and the
`LeafIsSafeDivergentResolve` regression class in
`plugins/flow-next/tests/test_tracker_capabilities.py`.

## Prevention
Two independent `resolve()`/`realpath()` calls compared against each other is a
Windows flake smell — normalize one side lexically against the other instead.
Regression shape that actually catches it: patch `Path.resolve` so the LEAF
returns an abbreviated (8.3-style) spelling while the base resolves fully, and
assert the in-tree leaf is still accepted — plus keep explicit `..`,
outside-absolute, symlinked-component, and symlinked-leaf refusals so the fix
cannot be "simplified" into a hole.

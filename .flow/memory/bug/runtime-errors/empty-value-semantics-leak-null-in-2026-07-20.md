---
title: "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T"
date: "2026-07-20"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [config-snapshot, empty-values, truthiness, fn-110]
problem_type: runtime-error
symptoms: "Merged subtree read returned null for a real {} default; empty --description-file wrote TBD instead of empty section"
root_cause: _walk_config_value empty-dict-means-default quirk reused on snapshot path; truthiness check on optional description string
resolution_type: fix
related_to: [bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27, bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19, bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19]
---

## Problem
Snapshot-based merged config reads (fn-110.1 `config get` subtree support) routed through `_walk_config_value`, which carries a historical empty-dict-means-default quirk: a genuinely empty dict `{}` (e.g. the `tracker.perTracker.labelMap` default) was converted to `null` in subtree/merged reads. Separately, `task create --description-file` with an explicitly empty (or heading-only) file fell into a truthiness check and wrote the `TBD` stub instead of the intentionally empty section that `task set-spec --description` produces.

## What Didn't Work
Reusing `_walk_config_value` directly for the snapshot merged path (inherits the quirk), and `description.rstrip() if description else "TBD"` (truthiness collapses empty-string into omitted).

## Solution
flowctl.py: snapshot merged reads use a sentinel-aware probe (`_tree_probe` + `_CONFIG_RAW_SENTINEL` -> None only when the key is truly absent), documented as a deliberate divergence from the snapshot-less `get_config` quirk (plugins/flow-next/scripts/flowctl.py:1613-1631). Create-time description uses `description is not None` so only an omitted flag falls back to TBD (flowctl.py:6570-6576). Regression tests: empty-map subtree + snapshot sentinel-awareness (test_config_snapshot.py), empty-file + heading-only description (test_task_create_files.py).

## Prevention
When adding a fast path that mirrors an existing read/write, test the degenerate values explicitly: empty dict, empty string, heading-only content. Truthiness checks on optional string params are a smell - use `is not None` when "" is a meaningful value. Empty-value equivalence tests between old and new paths catch quirk leakage.

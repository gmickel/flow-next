---
title: Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp
date: "2026-06-05"
track: bug
category: security
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-55, codex-delegation, rollback, git-clean, path-sanitization, review-feedback]
problem_type: security
symptoms: git clean could delete a pre-existing untracked file (whitespace/backslash aliasing) or degrade into a bare clean on an empty path set
root_cause: sanitize_rollback_path trimmed/normalized output bytes (aliasing distinct paths) and the documented git-clean lacked a non-empty guard
resolution_type: fix
---

## Problem
The deterministic scoped-rollback helper for the Codex implementation-delegation path (`flowctl codex rollback-plan`, which feeds `git clean -fd` ONLY the codex-created untracked files) had three aliasing/safety bugs that a Carmack-level review surfaced across three rounds — each one could silently `git clean` a file the user owns, or degrade into a catastrophic bare clean.

## What Didn't Work
1. **`rel.strip()`** in `sanitize_rollback_path()` — collapsed a DISTINCT codex-created path `" new.py"` (leading space) onto a pre-existing untracked `"new.py"`, so rollback could delete the user's file. Trimming a git-`-z` path is never safe: leading/trailing whitespace is part of the filename.
2. **Backslash normalization** (`s.replace("\\", "/")` used for BOTH the checks AND the returned value) — rewrote `dir\file.py` to `dir/file.py`, aliasing it onto a pre-existing `dir/file.py`. Returning a rewritten path has the same hazard as trimming.
3. **`jq -j '.rollback_paths[] + " "' | xargs -0` git-clean** in the docs — a literal-space join under `xargs -0` (NUL splitter) concatenated all paths into one mangled arg; and with an empty (all-rejected) set, the bare `git clean -fd --` wipes ALL untracked output (github/copilot-cli#1675).

## Solution
- Never trim, never rewrite output bytes: return the raw `rel` verbatim; reject (don't normalize) any path containing a literal backslash; run all checks (`.flow/`, traversal, absolute, bare-dir) on the raw string. (`plugins/flow-next/scripts/flowctl.py` `sanitize_rollback_path` / `_rollback_reject_reason`)
- Validate schema array ITEM types: `files_modified` / `issues` must be arrays of strings (the `--output-schema` declares `items: {type: string}`); a non-string item then `valid_schema:false` then task_failure (no blind commit).
- Add `flowctl codex rollback-plan --print0` (NUL-delimited sanitized paths, empty set then no output) + a MANDATORY `jq '.rollback_paths | length' > 0` guard in BOTH the reference and worker.md before any clean.

## Prevention
For any helper that computes paths fed to `git clean -fd` / `rm`: (1) treat the path string as opaque bytes — never `strip()`, never rewrite separators in the RETURNED value (rewrite only a throwaway copy used for membership checks); (2) reject ambiguous inputs (backslash, absolute, `..`, bare dir) rather than canonicalize them; (3) always guard the destructive command against an empty argument list (an empty list is the bare-clean footgun). Add regression tests that put a DISTINCT odd-char path next to a pre-existing plain path and assert the plain one never lands in the cleanup set.

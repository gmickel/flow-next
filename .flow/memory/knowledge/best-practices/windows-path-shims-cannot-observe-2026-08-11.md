---
title: Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT
date: "2026-08-11"
track: knowledge
category: best-practices
module: plugins/flow-next/tests
tags: [windows, ci, subprocess, spawn-count, git-shim]
applies_when: "Writing a test that counts or intercepts subprocess spawns via a PATH shim, or debugging a windows-latest-only empty-shim-log failure."
---

## What happened

fn-180.3's spawn-budget tests used a PATH `git` shim (POSIX script logging argv, then exec real git). Green on macOS/Linux; on windows-latest the log stayed empty and assertions failed 0 != 1. A `git.bat` variant also failed.

## Root cause

Windows `CreateProcess` (what Python `subprocess` uses for list-form argv) resolves the executable by appending `.exe` only - it never consults PATHEXT, so neither an extensionless script nor a `.bat`/`.cmd` on PATH can intercept a `["git", ...]` spawn. PATH-shim interception of subprocess calls is structurally impossible on Windows without shipping a real `.exe`.

## What to do instead

Skip spawn-accounting tests on `os.name == "nt"` with the reason stated (the counted property is OS-independent Python logic; POSIX CI legs carry it), or count spawns in-process via `mock.patch` on `subprocess` when the code under test runs in-process. Precedent: `test_evidence_reachability.py` `EvidenceReachabilitySpawnBudgetTest` skipIf.

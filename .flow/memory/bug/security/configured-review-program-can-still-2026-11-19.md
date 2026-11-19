---
title: Configured review program can still come from the checkout after argv leaves con
date: "2026-11-19"
track: bug
category: security
module: plugins/flow-next/scripts/flowctl.py
tags: [review, command-backend, windows, path-resolution]
problem_type: security
symptoms: "Machine-local argv still ran a checkout program via relative path, Windows cwd lookup, symlink or unresolved name"
root_cause: Only the argv source was moved; executable selection still depended on the checkout
resolution_type: fix
related_to: [bug/security/managed-review-transport-must-bound-2026-09-08]
---

## Problem
A review backend that runs a program named in config must not let the branch under review choose that program. Moving the argv into a machine-local environment variable closed the obvious hole (tracked `review.commands`). The program could still come from the checkout in four ways: a relative path resolved from the checkout as the working directory, a bare name that Windows looks up in the parent's current directory before PATH, a checkout symlink whose target lies outside, and a bare name PATH missed, passed through unresolved so the child looked it up again from another directory.

## What Didn't Work
Setting `cwd` for the child process only moves where the child runs. Windows `CreateProcess` still selects the executable using the parent's current directory. Checking only `realpath(program)` passes a checkout symlink, because the symlink, not its target, is what the checkout controls.

## Solution
`_review_command_argv` in `plugins/flow-next/scripts/flowctl.py` fixes the program before any round is reserved:
- a bare name resolves through `shutil.which`, taken from the current directory with `abspath`, and a miss is refused;
- a relative path is joined to home;
- both the normalized path and its realpath are checked against the repo root;
- the Windows `.cmd`/`.bat` refusal runs on the resolved path.
The spawn then gets that absolute program and starts in the home directory.

## Prevention
For any feature that executes a configured program on behalf of a review or other untrusted-input flow, test executable selection itself: a relative path, a bare-name current-directory hit, a symlink inside the checkout, a PATH miss, and resolution through PATHEXT. Testing only where the value is read misses all of these.

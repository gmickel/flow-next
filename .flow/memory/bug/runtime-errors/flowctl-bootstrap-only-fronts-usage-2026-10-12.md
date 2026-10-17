---
title: flowctl bootstrap only fronts usage/--help; process-wide settings go in main()
date: "2026-10-12"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [flowctl, launcher, bootstrap, muse, install-integrity]
problem_type: runtime-error
symptoms: flowctl commands wrote __pycache__ into the plugin install despite a bootstrap fix
root_cause: scripts/flowctl execs flowctl.py directly for every command except usage and --help
resolution_type: fix
---

## Problem
A process-wide flowctl setting (no bytecode writes into the install) was added to `flowctl_bootstrap.py`, and the regression test called the bootstrap directly. The `scripts/flowctl` launcher only routes the exact `usage` and `--help` invocations through the bootstrap; every other command execs `flowctl.py`, so `flowctl config get` still wrote `flowctl_tracker/__pycache__` into the plugin install. Muse Code disables a plugin's agents when installed files change.

## What Didn't Work
Setting `sys.dont_write_bytecode` in the bootstrap's `main()` and testing the bootstrap with a fake `flowctl.py`.

## Solution
Set it at the start of `flowctl.py` `main()`, which both the launcher and the bootstrap call, and test a tracker-importing command through the shipped launcher on a copied `scripts/` tree, asserting no `__pycache__` appears.

## Prevention
Anything every flowctl command must do belongs in `flowctl.py` `main()`, not the bootstrap. Test it through `scripts/flowctl` the way a user runs it, with a command that imports `flowctl_tracker`.

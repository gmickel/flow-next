---
title: Flag substring assertion passes when a longer sibling flag is present
date: "2026-09-23"
track: bug
category: test-failures
module: plugins/flow-next/tests/test_spec_id_routing_prose.py
tags: [prose-test, cli-flags, false-green]
problem_type: test-failure
symptoms: prose guard stayed green with --tracker-id removed
root_cause: --tracker-id is a substring of --tracker-identifier
resolution_type: fix
---

## Problem
A prose guard asserted `"--tracker-id" in line` for every `spec create --tracker-first` line. `--tracker-id` is a prefix of `--tracker-identifier`, which every such line already carries, so the guard passed with the durable id removed.

## What Didn't Work
Plain substring `assertIn` on a CLI flag whose name prefixes a sibling flag.

## Solution
Match the whole option token: `assertRegex(line, r"(?<!\S)--tracker-id(?=[\s=])")` in plugins/flow-next/tests/test_spec_id_routing_prose.py.

## Prevention
When a test pins a flag, check whether another flag shares its prefix, and prove the guard red by stripping the flag in memory (mock Path.read_text) before trusting it.

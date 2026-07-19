---
title: Forced-color git grep output defeats regex post-filter (SGR escapes)
date: "2026-07-19"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [git, subprocess, regex, export, ansi]
problem_type: runtime-error
symptoms: Batched export git grep silently dropped removed-symbol refs when color.grep=always
root_cause: SGR escape's trailing 'm' is a word char; word-boundary lookbehind failed on colored match text
resolution_type: fix
related_to: [bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27]
---

## Problem
fn-109.2 batched the export's per-symbol `git grep` fan-out into OR'd multi-pattern calls and recovered per-symbol attribution with a Python word-boundary regex over each returned line. Codex review (conf 100) found that a forced-color git config (`color.grep=always`) wraps matches in SGR escapes even when piped; the escape's trailing `m` is a word character, so the lookbehind `(?<![0-9A-Za-z_])` failed and refs the old per-symbol grep kept were silently dropped.

## What Didn't Work
First instinct was to strip SGR from the line for matching while keeping the colored snippet in the payload (the reviewer's suggestion). That cannot restore byte parity: the batched grep colors EVERY chunk symbol on a shared line while each per-symbol grep colored only its own match, so colored snippets are per-invocation-dependent by construction.

## Solution
Pass `--color=never` on the batched `git grep` invocation (plugins/flow-next/scripts/flowctl.py `_export_removed_export_refs`), so the attribution regex runs on the exact raw bytes git matched and snippets are config-independent raw file content. Regression test pins match-only coloring (`color.grep.filename/linenumber/separator = normal`, `match = bold red` - host global gitconfig can color the other slots and mask the case) and asserts refs survive plus oracle parity modulo the old color bytes.

## Prevention
When post-filtering subprocess text output with regexes, force the tool into plain-output mode (`--color=never`, `--porcelain`, `-z`) instead of assuming pipe output is clean - user configs like `color.*=always` override the not-a-tty default. Parity tests against a sequential oracle should include a forced-color fixture.

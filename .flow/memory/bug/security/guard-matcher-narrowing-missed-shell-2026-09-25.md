---
title: Guard matcher narrowing missed shell control words and split redirect words
date: "2026-09-25"
track: bug
category: security
module: plugins/flow-next/scripts/hooks/ralph-guard.py
tags: [ralph-guard, shell-parsing, bypass]
problem_type: security
symptoms: if/then/do-wrapped codex exec and evidence-free flowctl done passed the guard
root_cause: executable position taken from the first segment word; redirect target read as one non-POSIX token
resolution_type: fix
---

## Problem
Replacing ralph-guard's raw-text `\bcodex\b` / ` done ` checks with executable-position matching (fn-255 R8) removed false positives but opened bypasses: `_segment_argvs` took shell control words (`if`, `then`, `do`, `{`) as the executable, so `if codex exec ...; fi` and `if true; then flowctl done ... ; fi` (no evidence) passed where the base blocked them. The receipt-redirect check read only the next non-POSIX shlex token, so `> "/tmp/receipts"/x.json` split into fragments and escaped.

## What Didn't Work
Tokenizing with `shlex(posix=False)` to keep quoted `>` out of redirect detection, and trusting the first word of a segment as the command.

## Solution
Strip `_SHELL_CONTROL_WORDS` in `_strip_argv_wrappers` before taking the executable (plugins/flow-next/scripts/hooks/ralph-guard.py); find unquoted `>` with a quote-aware scan and read the target as one POSIX shell word (`_redirect_targets`).

## Prevention
Every narrowing of a guard's matcher needs a paired "real violations stay blocked" table that includes control structures (if/then/do/brace groups) and adjacent-fragment words, run against both the base and the new code.

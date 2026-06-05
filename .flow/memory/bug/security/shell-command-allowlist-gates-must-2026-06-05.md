---
title: "Shell-command allowlist gates must tokenize argv, not substring-match"
date: "2026-06-05"
track: bug
category: security
module: plugins/flow-next/scripts/hooks/ralph-guard.py
tags: [fn-55, ralph-guard, codex-delegation, shlex, allowlist, bypass, security, review-feedback]
problem_type: security
symptoms: "Regex-based codex-exec allowance bypassed 5 ways: shell chaining, quoted-flag smuggling, -c MCP override, path traversal, -m --last"
root_cause: "Substring/regex matching over raw command text never models the command as argv, so flags can be smuggled into quoted args, positions, or option values"
resolution_type: fix
related_to: [bug/security/rollback-path-sanitizer-must-not-2026-06-05]
---

## Problem
A PreToolUse hook allowance that permits a dangerous CLI invocation (here `codex exec` delegation in `ralph-guard.py`) MUST validate the WHOLE Bash command as a single, fully-constrained argv — not by substring-matching required tokens. Codex impl-review (rp) found FIVE distinct bypasses across five review cycles on one regex-based allowlist, each verifiable: (1) shell chaining — `<canonical> ; codex exec --last` inherits the whole-command allowance; (2) quoted-token smuggling — all required flags packed into ONE quoted positional prompt arg, so the regex sees them but `codex exec` receives an arbitrary prompt and none of the flags; (3) arbitrary `-c key=value` override — an extra `-c mcp_servers.evil.command=...` re-enables MCP and silently defeats the load-bearing `--ignore-user-config`; (4) path traversal — `.flow/tmp/codex-x/../../tasks/y.json` prefix-matches the scratch dir yet escapes it; (5) flag-as-value — `-m --last` swallows `--last` as the model value, slipping past a per-option `--last` check.

## What Didn't Work
Substring/regex matching over raw command text (`re.search` for each required flag, an `-o` prefix check, a per-option `--last` reject). Each pass plugged one hole but left the structural flaw: the validator never modeled the command as argv, so flags could be smuggled into quoted args, positions, or option values.

## Solution
Tokenize with `shlex.split(posix=True)` (parse error -> block) and walk the resulting ARGV as a strict allowlist state machine where EVERY token must be one the canonical invocation emits — any unexpected token blocks. Plus: ban shell control operators in the raw string BEFORE tokenizing (shlex is not a parser; it tokenizes `;`/`&&`/`|` as words); require exactly-one-codex; restrict value-taking flags to exact expected values (`-c` to `model_reasoning_effort="(enum)"`, `-m` to a model charset with no leading dash, `-s` to `workspace-write`); require every singleton exactly once; constrain paths to exactly `[./].flow/tmp/codex-<id>/<canonical-basename>` (no nested dir, no `..`, no absolute); and reject the forbidden flag GLOBALLY (`if "--last" in tokens`), not just as a current-option token. See `plugins/flow-next/scripts/hooks/ralph-guard.py` `is_canonical_codex_delegation`.

## Prevention
For ANY security gate that allowlists a shell command: (a) model it as argv via a real tokenizer, never substring regex; (b) reject shell metacharacters before tokenizing; (c) every token must be expected (closed allowlist), so smuggled positionals/values are rejected by construction; (d) forbidden tokens get a GLOBAL membership check, not a positional one; (e) value-taking flags validate their value against an exact pattern; (f) path args require an exact canonical shape (basename pinned, no traversal). Write a regression test that EXECUTES the shipped predicate (and drives the real hook end-to-end) against each adversarial bypass, not just the happy path.

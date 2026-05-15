---
title: "fn-44.1 review cycle: --json contracts, HTML-comment nesting, setup file copy"
date: "2026-05-15"
track: bug
category: build-errors
module: "plugins/flow-next/scripts/flowctl.py, plugins/flow-next/templates/spec.md, plugins/flow-next/skills/flow-next-setup"
tags: [fn-44, scope-flag, impl-review, codex-review, argparse-choices, html-comments, setup-workflow, shell-quoting, exit-codes]
problem_type: build-error
symptoms: "Five NEEDS_WORK rounds on a single task: missing --json on subcommand, argparse choices=blocked JSON errors, nested HTML comments rendered as visible markdown, snippet referenced missing template, exit 1 for valid no-fire JSON output, stale .flow/bin local copy"
root_cause: "Multiple contract-surface invariants (--json everywhere, HTML comments don't nest, setup must own physical file install, plain-vs-JSON exit-code semantics differ) treated as happy-path concerns rather than enforced patterns"
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/codex-impl-review-false-positive-on-2026-05-09, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem

T1 of fn-44 (scope helper plumbing + canonical spec template + drift guard) triggered five rounds of NEEDS_WORK before SHIP. The findings clustered in three categories:

1. **Contract surface gaps** — AC said "all subcommands accept --json", but argparse `choices=` rejected invalid input BEFORE the command handler could emit JSON. `scope write-policy` was missing `--json` entirely. Result: invalid input emitted argparse text, not JSON — broke the helper contract.

2. **Markdown-format invariants ignored** — Spec template `<!--` comments cannot nest. The outer guidance block contained literal inner `<!-- scope: business -->` example strings; the first inner `-->` closed the outer block prematurely, exposing the rest as visible markdown.

3. **Cross-skill physical-install holes** — Setup snippets pointed at `plugins/flow-next/templates/spec.md` (the canonical path), but `/flow-next:setup` only copies `.flow/bin/flowctl`, `flowctl.py`, and `usage.md` into target projects. Result: snippets reference a path that doesn't exist in downstream projects.

4. **Same-version-refresh dead-branch** — Setup's "already installed, same version" path skipped Step 4 (file copy). When new files (`.flow/templates/spec.md`) needed to ship even on same-version refresh, this branch left them missing while docs pointed at them.

5. **Bash word-splitting ate quoted paths** — `flowctl scope resolve --json $ARGUMENTS` in SKILL.md used unquoted expansion. `/flow-next:interview --biz "docs/my spec.md"` would word-split into broken tokens.

6. **Exit-code semantics conflated** — `scope suggest --json` exited 1 for valid no-fire decisions. JSON callers use exit 0 for success; exit 1 looks like an error. Plain-mode 0/1 branch semantics need to differ from JSON-mode subprocess semantics.

7. **Stale local copy of flowctl.py** — `.flow/bin/flowctl.py` in this repo wasn't auto-refreshed when `plugins/flow-next/scripts/flowctl.py` updated. Repo instructions told agents to use `.flow/bin/flowctl`, but the local copy lagged. Multi-day blind spot.

## What Didn't Work

Initial implementation passed local smoke tests for the happy paths but missed:
- The contract-level invariant (`--json` everywhere) was treated as "happy-path JSON output works" rather than "EVERY output, including error paths, is JSON when --json is set".
- HTML-comment nesting was not on the radar — Python's frontmatter-style block looked syntactically clean to the writer but breaks the HTML parser.
- The shell-quoting hazard didn't show up because bare tests used positional tokens; the `$ARGUMENTS`-passthrough form was tested only with no-spaces inputs.
- Setup's same-version-refresh path was unchanged from pre-fn-44 — works for "just update docs" semantics but breaks the moment a non-docs file ships.

## Solution

- **Defer scope-validation to the command handler** (drop argparse `choices=`). Lets the handler emit `{"success": false, "error": ...}` JSON when `--json` is set, and stderr text otherwise. Apply this pattern to ANY subcommand with a `--json` flag — argparse choices and JSON contracts don't mix.
- **Add `--raw` flag** that accepts the raw user-arguments string and shlex-splits inside Python. SKILL.md uses `$FLOWCTL scope resolve --json --raw "$ARGUMENTS"` (quoted) — shell never word-splits, Python handles tokenization.
- **Differentiate exit-code semantics by mode** — plain mode = 0/1 branch (shell-call-friendly); `--json` mode = 0 for valid input regardless of decision (subprocess success), non-zero reserved for invalid input.
- **HTML comments**: never nest examples that contain literal `<!--` / `-->`. Use plain-text representation in guidance blocks. Verify via parser: 10 `<!--` must match 10 `-->`, balanced.
- **Setup file copy must be unconditional** on refresh — don't gate behind "version changed". Idempotent file copies are cheap; missing files are expensive.
- **`.flow/bin/flowctl.py` parity** — must be refreshed any time `plugins/flow-next/scripts/flowctl.py` is touched in a way that affects skill runtime. CLAUDE.md/AGENTS.md cross-link to in-project `.flow/bin/flowctl`, so the local copy is the user-facing surface.

## Prevention

- **CI / test pattern for subcommand contracts**: every new `--json` subcommand needs both happy-path AND invalid-input tests asserting JSON output on stderr/exit. The "contract" is that JSON callers never need to parse argparse text.
- **HTML-comment-balance check**: small parser test on any markdown template in `plugins/flow-next/templates/` that opens/closes a `<!--` block — count matches, no nested markers.
- **Bash-passthrough rule**: anywhere a skill uses `$ARGUMENTS` (Claude Code / Codex pass user-provided args as a single string), use `--raw "$ARGUMENTS"` with a flowctl subcommand that does in-process tokenization. Never `cmd $ARGUMENTS` unquoted.
- **Setup-changeset rule**: every PR adding a new file under `.flow/<path>` MUST update `/flow-next:setup`'s copy list AND `/flow-next:uninstall`'s removal list AND the success-summary.
- **`.flow/bin/` refresh hook**: add to pre-commit (or local-dev workflow) — when `plugins/flow-next/scripts/flowctl*` changes, also refresh `.flow/bin/`. Otherwise the repo's own self-host instructions stall.

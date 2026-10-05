---
title: "flowctl --json contracts, nested HTML comments, and scoped-diff review blind spots"
date: "2026-05-21"
track: bug
category: build-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-44, json-contract, argparse, exit-codes, html-comments, scoped-diff, impl-review, codex-review]
problem_type: build-error
symptoms: "Review rounds flagged --json missing on subcommands, stderr errors from choices= validation, plain-mode exit codes under --json, stray --> from nested comments, and findings about state before --base"
root_cause: Contract flags and comment syntax treated as happy-path concerns; a scoped review sees only the diff since its base
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
related_to: [bug/test-failures/test-production-path-not-parallel-construction-2026-05-21]
audit_consolidates: [bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/fn-442-review-both-pass-policy-2026-05-15, bug/build-errors/fn-445-review-r17-enforcement-beyond-2026-05-15, bug/build-errors/fn-447-review-cycle-scoped-diff-false-2026-05-15]
---

## Problem

The fn-44 work went through 10+ NEEDS_WORK rounds of codex impl-review across four tasks. Most of its lessons were tied to surfaces that no longer exist; these five still apply.

## Lessons

1. **`--json` reaches every subcommand.** A `--json` flag must be threaded through every subcommand in a parser tree, not just the top level. A subcommand that ignores it breaks the contract the flag exists for.
2. **`choices=` rejects before the handler runs.** `argparse` validates `choices=[...]` before the handler, so an unrecognized value sent to a `--json` command produces a plain stderr error, not a JSON error envelope. Either accept the value and reject it inside the handler, or document that the choice list is the contract.
3. **JSON mode exits 0 with a payload.** Plain mode may signal "did not fire" with exit 1; under `--json` the payload is the signal, so exit 0 with `{"fired": false}`. Do not carry plain-mode exit codes through to `--json` callers.
4. **HTML comments do not nest.** In `<!-- outer <!-- inner --> -->` the inner `-->` closes the outer comment and leaves a stray `-->` visible. Use one comment and keep any inner commentary as plain prose.
5. **A scoped review sees only its diff.** `flowctl <backend> impl-review --base <commit>` reviews changes since `<commit>`; a commit message explaining earlier state does not reach the reviewer. Put the evidence in the diff (a touched file or an inline comment) or pass an earlier `--base` to widen the window.

## Prevention

- When adding `--json` or another contract flag, grep every subcommand that should accept it and test the error path, not only the success path.
- Document the exit-code contract per output mode.
- Before rebutting a scoped-review finding about pre-existing state, check whether the evidence is inside the reviewed range.

---
title: "Test the production path, not a parallel construction"
date: "2026-05-21"
track: bug
category: test-failures
module: "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py"
tags: [testing, production-form, mock-patch, argparse-two-token, routing-table, dual-emit, review-feedback]
problem_type: test-failure
symptoms: "Codex flagged Major findings across review cycles where tests asserted against side-forms (hand-built dicts mirroring expected output, --flag=VALUE single-token variant when production uses --flag VALUE two-token) instead of driving the production code path"
root_cause: "Tests built parallel constructions (literal dict matching expected shape; alternate CLI wire-form; substring presence in whole document) instead of exercising the actual cmd_* function / production argparse form / per-row routing logic — making the tests pass while the real production path failed"
resolution_type: fix
related_to: [bug/build-errors/fn-44-review-cycle-lessons-2026-05-21]
audit_consolidates: [bug/test-failures/test-json-cli-output-via-cmd-directly-2026-05-09, bug/test-failures/test-the-production-wire-form-not-the-2026-05-15]
---

## Problem

Two recurring patterns where tests "covered the contract on paper" but never exercised the production code path:

**Pattern A: hand-built dict snippets instead of cmd_* invocation (fn-43 era)**

Unit tests for a CLI's JSON-output dual-emit contract initially asserted against hand-built dict snippets that mirrored the production payload structure. Tests passed locally and covered the right shape on paper, but never invoked `cmd_specs` / `cmd_show` / `cmd_next` / `cmd_status` / `cmd_checkpoint_save` themselves. Codex flagged Major @ 100 confidence: "the read-compat suite does not actually test the CLI JSON output contract it claims to cover." Drift between test and implementation could go undetected indefinitely.

**Pattern B: workaround wire-form instead of production wire-form (fn-44 era)**

Tests for `flowctl scope resolve --raw VALUE` (two-token form) pivoted to `--raw=VALUE` (single-token) when argparse rejected two-token with VALUE starting with `--` (`--biz`, `--scope=business`). The single-token form is a workaround; the SKILL.md path invokes the two-token form. Test passed while the skill path failed — the side-form masked a real production bug. Same task also: substring-presence test against whole-document text instead of per-row table-routing assertion against the actual SIGNAL_CATEGORIES routing constant.

## What didn't work

- Replicating `cmd_next`'s "blocked" payload as a literal dict and asserting against that — proved nothing about the function actually emitting that shape.
- Pivoting to `--raw=VALUE` single-token form to dodge argparse — production was two-token; test passed, production broke.
- Asserting "SIGNAL_CATEGORIES appears in workflow.md" as a proxy for "routing table maps each category to its destination" — substring presence ≠ per-row routing correctness.

## Solution

**Pattern A (dual-emit JSON output):**
- Build minimal `.flow/` fixtures with the two seeded shapes (e.g. 0.x alias-mode and 1.0 post-migration).
- Drive the production function: import `cmd_*` directly, prepare args, call it, capture `json_output` via `mock.patch`.
- Assert against the captured payload structure — that's the production contract.

**Pattern B (CLI wire-form):**
- Test the EXACT invocation the SKILL.md / shell scripts use. If SKILL.md calls `"$FLOWCTL" scope resolve --json --raw "$ARGUMENTS"` (two-token), the test invokes two-token via `subprocess.run([flowctl, "scope", "resolve", "--json", "--raw", value])`. No `--raw=` shortcut.
- For routing tables, assert PER-ROW: iterate the canonical SIGNAL_CATEGORIES constant and verify each row's destination appears in the right markdown section. Whole-document substring presence is not equivalent.

## Prevention

- **Never assert against parallel constructions.** Build a payload dict mirroring expected shape → red flag. Build the production output via `cmd_*` / `subprocess` → green.
- **Test the wire form callers use.** Grep callers in `skills/`, `agents/`, `scripts/` for the exact CLI invocation. If they use two-token, your test uses two-token. If they use `--flag=value`, your test does the same. No "equivalent" forms.
- **Routing-table tests iterate the source of truth.** If a constant defines the mapping (`SIGNAL_CATEGORIES`, `_CONFIG_KEY_ALIASES`), iterate it in the test and assert per-entry. Substring `in` checks are not routing tests.
- **`mock.patch` the seam that the production function actually writes through.** For dual-emit JSON, patch `json_output`; for `print(json.dumps(...))`, patch `print`. Wrong seam = test passes while production silently changes shape.

## See also

- `[[fn-44-review-cycle-lessons]]` — broader review-discipline patterns from the same era (contract enforcement, scoped-diff false-positives, R17/R21 guards)
- `plugins/flow-next/tests/test_read_compat.py` — exemplar of the `mock.patch` + `cmd_*` direct-drive pattern (17 cmd_* references confirmed)
- `plugins/flow-next/tests/test_acceptance_criteria_parser.py` — exemplar of per-form heading regex testing (canonical + 2 legacy forms, each tested independently)

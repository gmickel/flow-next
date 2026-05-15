---
title: "Test the production wire form, not the workaround"
date: "2026-05-15"
track: bug
category: test-failures
module: "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py"
tags: [fn-44, impl-review, codex-review, argparse-two-token, routing-table-assertions, production-form, test-quality]
problem_type: test-failure
symptoms: "Codex flagged 2 Majors across review cycles: tests pivot to --raw=VALUE workaround instead of fixing flowctl two-token form; SIGNAL_CATEGORIES constant defined but never consumed for per-row routing"
root_cause: Tests verified against side-forms (--raw=VALUE single-token) and whole-document substring presence instead of production wire form (--raw VALUE two-token) and per-row table parsing — work-arounds masked real bugs
resolution_type: fix
---

## Problem
fn-44.9 (final-gate test task) hit two impl-review NEEDS_WORK rounds. Both
findings exposed the same pattern: tests claiming to cover a contract but
exercising a side-form or substring search rather than the actual production
wire format / per-row behavior.

1. **Production form vs workaround form** — `flowctl scope resolve --raw VALUE`
   (two-token form) is what SKILL.md invokes via `"$FLOWCTL" scope resolve
   --json --raw "$ARGUMENTS"`. argparse rejects the two-token form when VALUE
   begins with `--` (`--biz`, `--scope=business`). My initial test pivoted to
   `--raw=VALUE` (single-token form) to "work around" the issue — but that
   masked a real production bug. Codex pass 1 flagged: tests pass while the
   skill path fails.

2. **Substring presence vs per-row routing** — the R24 routing table has 9
   rows mapping signal categories to markdown destinations. My initial test
   defined the canonical mapping as a `SIGNAL_CATEGORIES` constant then never
   used it — only checked whole-document substring presence. Swapped rows
   (e.g., MVP → Goal & Context instead of Boundaries) would pass silently.
   Codex pass 2 flagged: constant defined but unconsumed, per-row contract
   not actually tested.

## What Didn't Work
- Pivoting `_resolve()` to use `--raw=VALUE` single-token form to "bypass"
  argparse rejection. Tests passed locally but the production path stayed
  broken. The right move was either (a) fix flowctl to handle the two-token
  form, or (b) keep tests in the two-token form to surface the real bug.
- Defining the canonical mapping as a constant then verifying via
  whole-document `assertIn` — substring presence is not a per-row contract.
  The constant looks like coverage but isn't.

## Solution
1. **Fuse `--raw VALUE` → `--raw=VALUE` in flowctl pre-processing**
   (`flowctl.py:22348`). Before argparse sees the args, walk `sys.argv` and
   rewrite the two-token form to single-token. Now the production
   invocation works for every value shape (`--biz`, `--scope=both`,
   `--biz fn-1`, ``""``).
2. **Add `TestScopeResolveProductionInvocationForm` suite** that exercises
   the TWO-TOKEN form by default (`fused=False`). Coverage spans every
   single-flag value the previous workaround masked.
3. **Add `_parse_routing_table()` helper** to extract the 9-row routing
   table from `workflow.md`, plus `test_each_row_routes_to_required_
   destinations` that asserts per-row: category substring on expected
   row, every required destination substring in the row's destination
   cell. Swap regressions now fail loudly.
4. **R23 behavior tests via fixture spec markdown** — drive
   `flowctl scope write-policy` against fixtures with populated /
   empty / mixed section states; verify the policy mechanically enforces
   the byte-for-byte preservation contract (writable/preserved disjoint,
   aux out-of-scope, placeholder-only replacement, FLAT/SUBSTRUCTURED
   transitions, append-only R-IDs via absence of renumber-signal).

## Prevention
- **Test the production wire form, not the workaround.** When argparse /
  the CLI / the shell rejects a value shape that the production path
  uses, fix the CLI rather than the test. A test that uses
  `--raw=VALUE` while the skill uses `--raw VALUE` is a test that can
  pass against broken production code. Symmetric to the fn-43.X
  "drive cmd_* directly, not hand-built dict snippets" rule — drive
  the real wire form, not a parallel construction.
- **Constants must be consumed structurally.** If you define a
  `SIGNAL_CATEGORIES` / `CANONICAL_MAPPING` constant and only use it
  for whole-document substring checks, the constant is decoration, not
  contract. Per-row / per-mapping assertions force the test to
  actually validate the mapping shape. Catches swap regressions that
  substring presence misses.
- **codex:gpt-5.5:high catch rate on fn-44 final-gate**: 2 review
  cycles to reach SHIP on a comprehensive test-only task. Both
  findings were the same pattern (tests-cover-the-wrong-form) — a
  pattern worth watching for in future test-writing tasks.

---
title: "Test the production path, not a parallel construction"
date: "2026-05-21"
track: bug
category: test-failures
module: "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py"
tags: [testing, production-form, mock-patch, argparse-two-token, routing-table, dual-emit, review-feedback, api-surface]
problem_type: test-failure
symptoms: "Review flagged Major findings where tests asserted against side-forms (hand-built dicts mirroring expected output, a --flag=VALUE form the callers never use, an artifact read beside the command under test) instead of driving the production code path"
root_cause: "Tests built parallel constructions (literal dict matching the expected shape; alternate CLI wire form; whole-document substring presence; values read from a sidecar) instead of exercising the cmd_* function, the production argparse form, or the command's real output"
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
related_to: [bug/build-errors/fn-44-review-cycle-lessons-2026-05-21]
audit_consolidates: [bug/test-failures/test-json-cli-output-via-cmd-directly-2026-05-09, bug/test-failures/test-the-production-wire-form-not-the-2026-05-15]
---

## Problem

Three recurring patterns where tests "covered the contract on paper" but never exercised the production code path:

**Pattern A: hand-built dict snippets instead of cmd_* invocation (fn-43 era)**

Unit tests for a CLI's JSON-output contract asserted against hand-built dicts that mirrored the production payload, and never invoked `cmd_specs` / `cmd_show` / `cmd_next` / `cmd_status` themselves. Review flagged it Major at confidence 100: the suite did not test the output contract it claimed to cover, so drift between test and implementation could go unnoticed indefinitely.

**Pattern B: workaround wire form instead of production wire form (fn-44 era)**

A test for a two-token flag (`--raw VALUE`) switched to the single-token `--raw=VALUE` form when argparse rejected a value starting with `--`. The skill invokes the two-token form, so the test passed while the skill path failed. The same task asserted that a constant's name appeared somewhere in a workflow file as a proxy for "the routing table maps each row to its destination".

**Pattern C: invoking one surface, asserting another (chart era)**

A spec said per-briefing `status` in `chart show --json` was the source of truth for capture-readiness. That command carries only `briefing_count` (`compact_chart_metadata`). The test called `chart show --json`, asserted `briefing_count`, then read the statuses from the chart sidecar, so it looked like it pinned a public contract and did not. The review's literal suggestion (assert the statuses from `chart show --json`) would have meant adding a projection the acceptance said stays unchanged.

## What didn't work

- Replicating `cmd_next`'s "blocked" payload as a literal dict and asserting against that: it proved nothing about what the function emits.
- Switching to `--raw=VALUE` to dodge argparse: production was two-token; the test passed and production broke.
- Whole-document substring presence as a stand-in for per-row routing correctness.
- Building a new surface to satisfy a finding that presupposed it.

## Solution

**Pattern A:** build minimal `.flow/` fixtures, import and call the `cmd_*` function, capture `json_output` via `mock.patch`, and assert the captured payload.

**Pattern B:** test the exact invocation the skill or script uses: if it calls the two-token form, the test does too (`subprocess.run([flowctl, ..., "--raw", value])`). For routing tables, iterate the constant that defines the mapping and assert each row's destination.

**Pattern C:** dump the command's real keys once in a throwaway repo, then pin the statuses where they live (the chart record's `briefings[]`) with a comment saying why that artifact is the authority, keep `chart show --json` pinned as the unchanged projection, and cross-check from public output that does report them. Decline the part of the finding that contradicts the acceptance, with the contradiction stated in the re-review message (`plugins/flow-next/tests/test_chart_briefing.py`).

## Prevention

- **Never assert against parallel constructions.** A payload dict built to mirror the expected shape is a red flag; output produced by `cmd_*` or `subprocess` is the contract.
- **Test the wire form callers use.** Grep callers in `skills/`, `agents/` and `scripts/` for the exact invocation and use the same form.
- **Routing-table tests iterate the source of truth** and assert per entry. A substring `in` check is not a routing test.
- **`mock.patch` the seam the production function writes through.** For dual-emit JSON, patch `json_output`; for `print(json.dumps(...))`, patch `print`.
- **A test that invokes command A but reads artifact B is a lie by adjacency.** Assert what A returns, or say in a comment why B is the authority. Spec prose names surfaces loosely; dump the real keys before claiming to pin one.
- **Decline-with-evidence is a valid review outcome** when the requested fix would contradict an acceptance criterion; never expand a public envelope to make a comment go away.

## See also

- `plugins/flow-next/tests/test_flow_gitignore.py`: drives `cmd_init` directly and captures `json_output` with `mock.patch`.
- `plugins/flow-next/tests/test_acceptance_criteria_parser.py`: tests each accepted heading form independently.

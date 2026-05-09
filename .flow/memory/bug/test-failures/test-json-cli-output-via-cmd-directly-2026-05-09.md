---
title: "Test JSON CLI output via cmd_* directly, not hand-built dict snippets"
date: "2026-05-09"
track: bug
category: test-failures
module: plugins/flow-next/tests
tags: [fn-43, testing, cli-json-output, dual-emit, mock-patch, subprocess, review-feedback]
problem_type: test-failure
symptoms: Codex flagged tests asserting against hand-built dict snippets that never invoked the real cmd_* function
root_cause: Tests built a literal payload dict mirroring expected shape rather than driving cmd_* and capturing json_output
resolution_type: fix
related_to: [bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09]
---

## Problem
Unit tests for a CLI's JSON-output dual-emit contract initially asserted hand-built dict
snippets that mirrored the production payload structure. The tests passed locally and
covered the right shape on paper, but never invoked `cmd_specs` / `cmd_show` /
`cmd_next` / `cmd_status` / `cmd_checkpoint_save` themselves. Codex review caught it on
the first pass with `Major @ 100` confidence — "the read-compat suite does not actually
test the CLI JSON output contract it claims to cover."

## What Didn't Work
Replicating cmd_next's "blocked" payload as a literal dict and asserting against that —
proved nothing about the function actually emitting that shape. Drift between test and
implementation could go undetected indefinitely.

## Solution
- Build minimal `.flow/` fixtures with two seeded shapes: 0.x alias-mode (`epics/` +
  `next_epic` + legacy `epic` task field) and 1.0 post-migration (sentinel + `specs/` +
  canonical `spec`).
- Capture `flowctl.json_output` via `mock.patch.object(flowctl, "json_output", ...)`
  inside an `_chdir(tmp)` context so the function-under-test executes against the
  fixture and writes to our captured-dict instead of stdout.
- Drive `cmd_specs / cmd_show / cmd_next / cmd_status / cmd_checkpoint_save /
  cmd_migrate_rename` directly with `argparse.Namespace(...)` instances.
- Add ONE belt-and-braces subprocess test (`subprocess.run([sys.executable, FLOWCTL,
  "status", "--json"], cwd=tmp)`) that actually drives the binary on the wire and
  parses stdout — confirms json_output mocking didn't accidentally pass while the
  real CLI was broken.

## Prevention
For any test of a CLI's JSON output contract, **drive the real `cmd_*` function**:

1. Build a real on-disk fixture (`.flow/`, `meta.json`, etc) under `tmp_path`.
2. `_chdir(tmp)` so `get_repo_root()` falls back to cwd → finds the fixture.
3. `mock.patch.object(module, "json_output", lambda data, success=True: captured.update(data))`.
4. Call `cmd_X(argparse.Namespace(...))` and assert against `captured`.

NEVER assert against a hand-built dict that mirrors the expected payload — that's a
dependency-free echo chamber. The test must execute the function whose output it
claims to verify.

For belt-and-braces wire-level coverage on at least one representative command, add
a `subprocess.run([sys.executable, FLOWCTL_PY, ...])` round-trip + `json.loads(stdout)`.
That catches "the in-process mock would have caught a real bug, but did the production
function reach `print()` at all?" type regressions (e.g. argparse mis-routing,
swallowed exceptions, stdout pollution from the migration banner).

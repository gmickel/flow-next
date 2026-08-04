---
title: Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid
date: "2026-08-04"
track: bug
category: test-failures
module: plugins/flow-next/tests/test_normalize_section_content.py
tags: [fn-120, windows, encoding, cp1252, utf-8, 8.3-short-path, geteuid, skipif, json-stdout]
problem_type: test-failure
symptoms: flowctl --file/--acceptance-file exits 1 with empty stderr on windows-latest; task_create_files errors at import
root_cause: "test fixtures written in the parent's locale encoding (cp1252) against a strict-UTF-8 production reader, plus os.geteuid() referenced at class-body decoration time on NT"
resolution_type: fix
---

## Problem
Two Windows-only test failures were recorded in the fn-120 characterization as "CLI `--file` args fail from 8.3 short paths". Neither was a path bug.

1. `test_normalize_section_content` CLI e2e wrote its acceptance fixtures with a bare `Path.write_text()`. On Windows that encodes as cp1252, and production `read_text_or_exit()` reads `--acceptance-file` / `--file` as strict UTF-8, so `flowctl` correctly exited 1 with `Acceptance file unreadable: ... 'utf-8' codec can't decode byte 0x96`. The 8.3 path in the message (`C:\Users\RUNNER~1\...`) was only the temp dir, not the defect.
2. The failure LOOKED opaque because `--json` errors are printed as JSON on **stdout**, while the test's assertion message interpolated only `proc.stderr` — the CI log showed `failed: ` with an empty tail.
3. `test_task_create_files` called `os.geteuid()` in a `skipIf` decorator at class-body time; on NT that attribute does not exist, so the whole module failed to import.

## What Didn't Work
Pinning the parallel runner's child-output decode to `encoding="utf-8", errors="replace"` looked like a free portability win. It is not: parent and child share the locale (cp1252 on both sides on Windows), so the transport was already symmetric, and forcing UTF-8 on only the parent turns legitimately-decodable cp1252 diagnostics into U+FFFD. The reviewer-suggested alternative — `PYTHONIOENCODING=utf-8` on the runner's children plus a strict decode — hands all 182 test files a UTF-8 console, so the Windows leg stops representing a real cp1252 console and can no longer catch the flowctl print-crash class (fn-120.1's reveval U+2192 failure). Reverted; runner transport is a deliberate, separately-owned decision.

## Solution
- Explicit `encoding="utf-8"` on every fixture write/read that feeds a production `--file` argument (`plugins/flow-next/tests/test_normalize_section_content.py`).
- Assertion messages report BOTH streams, ASCII-escaped via a local `_ascii()` helper, so a cp1252 pipe cannot mask a failure with a `UnicodeEncodeError`.
- Real 8.3 coverage via `ctypes.windll.kernel32.GetShortPathNameW` (never a hand-built `~1` string), asserting drive letter + absoluteness, plus a portable long-path-with-spaces + UTF-8 case.
- POSIX permission premise guarded with `skipUnless(os.name == "posix")` + `getattr(os, "geteuid", lambda: -1)()` — the repo's existing pattern (`test_spec_create_plan_file.py:288`, `test_setup_block_helper.py:188`).

## Prevention
- Any test fixture that feeds a `--file`/`--acceptance-file`/`--description-file` argument MUST pass `encoding="utf-8"`; production reads are strict UTF-8 by design and must stay that way.
- Any test asserting a `flowctl ... --json` subprocess succeeded must print stdout as well as stderr; `--json` errors never reach stderr.
- Never call `os.geteuid()` / `os.getuid()` unguarded — including inside decorators, which run at import time on every platform.
- Keep non-ASCII out of unittest FAILURE MESSAGES on Windows-run files (escape it); keep it in the assertion values.

# fn-120 Windows test-corpus compatibility sweep

> STUB (2026-07-20, fn-119 fallout). fn-119's parallel entrypoint expanded windows CI unit coverage from 29/87 files to 81/87; the remaining 6 are excluded ONLY on windows (see the loud EXCLUDES block in .github/workflows/test-flow-next.yml) with per-file causes captured from the first-ever full-corpus windows run (run 29754617049, fn-119 PR #219).

## Goal & Context

Make the 6 excluded files pass on windows-latest and empty the CI exclusion list. Every exclusion prints on every run (runner --exclude is never silent); this spec is the tracked owner of that list.

## The 6 files and their observed causes

1. test_backend_spec.py - HANGS (rc=124 at 900s per-file timeout). Cause unknown; first suspect is a subprocess waiting on stdin or a POSIX-only fixture. Investigate first.
2. test_flow_gitignore.py - 2F+1E: FLOW_GITIGNORE_AUTO_HEADER contains a non-ASCII dash; test read-back decodes as cp1252 (mojibake assert). Fix: explicit encoding="utf-8" on test-side reads (and audit flowctl-side writes).
3. test_gate_receipt.py - 1F+1E: literal-backslash-filename test is conceptually impossible on NT (backslash IS the separator) -> skipUnless posix; TTL-race test uses a #!/bin/sh git shim that can never fire on windows -> skip or a .cmd shim.
4. test_normalize_section_content.py - 2F: CLI e2e task create/set-acceptance --file fails rc=1 with 8.3 short paths (RUNNER~1). Reproduce with a short-path tmpdir; likely path normalization in flowctl or the test harness.
5. test_reveval_parse_guard.py - 1E: end-to-end guard errors on windows (traceback truncated in log; reproduce locally/CI with -v).
6. test_task_create_files.py - 1E: single error, likely same class as 4.

## Boundaries

- Wins must come from test-harness portability or real flowctl windows bugs; never weaken assertions to pass.
- Remove files from the CI EXCLUDES block in the same commit that fixes them.
- smoke/ci_test harnesses untouched (already windows-green).

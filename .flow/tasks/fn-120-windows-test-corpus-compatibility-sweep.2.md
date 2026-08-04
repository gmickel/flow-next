---
satisfies: [R4, R5, R7, R10]
---
# fn-120-windows-test-corpus-compatibility-sweep.2 Reproduce and fix real Windows 8.3 path failures

## Description
Reproduce and fix normalize's Windows short-path failure and independently remediate task-create's actual Windows portability failure.

**Size:** L
**Files:** plugins/flow-next/tests/test_normalize_section_content.py, plugins/flow-next/tests/test_task_create_files.py, plugins/flow-next/scripts/flowctl.py or shared test helpers only when evidence identifies the owner, .github/workflows/test-flow-next.yml

### Approach

Run each file independently with verbose/bounded output on `windows-latest`. For normalize, capture the traceback and create a deterministic fixture that passes a real valid short path (observed `RUNNER~1` shape) through the production CLI `--file` contract. For task-create, start from the current `os.geteuid()` evidence: guard only the POSIX permission premise while keeping every portable assertion active, unless Task 1's fresh characterization proves a different owner. Do not assume the errors share a root cause.

For normalize, test short-form and normal long-form paths, spaces, drive letters, and UTF-8 contents. Remove each exclusion atomically with the proven fix and green Windows run.

<!-- Updated by plan-sync: fn-120.1's fresh windows-2025 characterization (930cd764, run 30902994209) confirms test_task_create_files fails on an unguarded os.geteuid() call -- no alternate/shared cause with normalize was found, so the "unless fresh characterization proves a different owner" branch above does not trigger; proceed with the independent guard. Host review also flagged scripts/run_tests_parallel.py:153 (child spawn uses universal_newlines=True with no encoding kwarg -> cp1252 pipes on Windows) as a candidate root cause for the encoding-failure class this task's short-path fixtures sit next to -- worth checking during this task's investigation. -->

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_normalize_section_content test_task_create_files -q
```
## Acceptance
- [ ] Both files are isolated independently and exact Windows tracebacks are captured before remediation.
- [ ] Normalize regression fixtures exercise a real valid Windows 8.3/short path, not a mocked separator string; valid short and long `--file` paths with spaces/drive letters/UTF-8 content work through the real CLI.
- [ ] Task-create guards the POSIX-only permission premise (`os.geteuid()` or evidenced equivalent) while all portable tests continue running on Windows.
- [ ] A shared fix is used only if evidence proves one root cause; otherwise each owner receives a narrow fix.
- [ ] Both exclusions are removed in the same commit(s) as their fixes and focused Windows runs are green.
- [ ] Workflow run URL/ID is recorded; POSIX focused tests remain green.
## Done summary
Cleared the last two deterministic Windows exclusions (fn-120 R4/R5) with real windows-latest evidence, after proving both recorded "8.3 short-path" signatures wrong at the root.

Root causes (each isolated independently; no shared cause — spec decision 3):
- test_normalize_section_content: the two failing CLI e2e cases wrote their acceptance fixtures with a bare `write_text()`. On Windows that emits cp1252 (U+2013 -> 0x96, U+2014 -> 0x97) and production reads `--acceptance-file` / `--file` as strict UTF-8, so flowctl correctly exited 1 with "Acceptance file unreadable: ... 'utf-8' codec can't decode byte 0x96". The `RUNNER~1` in the CI message was just the temp dir. Reproduced locally byte-for-byte (rc=1, empty stderr) by writing the same fixture as cp1252 through the real CLI. The failure looked opaque because `--json` errors print to STDOUT while the assertion interpolated only stderr — that is fixed too (both streams, ASCII-escaped via `_ascii()` so a cp1252 pipe cannot mask a failure with UnicodeEncodeError).
- test_task_create_files: `os.geteuid()` in a `skipIf` decorator runs at class-body/import time and does not exist on NT — the whole module errored on import. Guarded with the repo's existing pattern: `skipUnless(os.name == "posix")` for the chmod-000 read-denial premise (NT chmod only toggles read-only, so the fixture cannot express its precondition) plus `getattr(os, "geteuid", lambda: -1)()` for the root case. The production "unreadable" branch stays covered on every platform by the directory-as-path case.

New regressions for the real `--file` contract (R4): a portable long path with spaces carrying UTF-8 content, and a Windows-only case driving the filesystem's OWN 8.3 short name from `GetShortPathNameW` (drive letter + absoluteness asserted; documented skip only if the volume disables 8.3 generation) — never a hand-built `~1` or slash-swapped string. Windows CI confirms it RAN (ran=28, skipped=0).

Both exclusions were removed in the same commit as their fix (R7). Reverting either fixture change re-breaks the file on windows-latest.

Investigated the plan-sync candidate (`run_tests_parallel.py` child decode) and deliberately left it alone after codex review: parent and child already share the locale, so the transport was symmetric and there was no live corruption; the only alternative that gives exact diagnostics (`PYTHONIOENCODING=utf-8` on children) would hand all 182 files a UTF-8 console and destroy the Windows leg's ability to catch the real cp1252 print-crash class fn-120.1 hit. Windows run 30913423957 is recorded as the evidence that a Windows child's own unittest stream is cp1252. Runner transport is left to fn-120.3 as an explicit decision.

Only `test_backend_spec.py` remains on the Windows EXCLUDES list (fn-120.3). Final SHA ec437e87: windows-latest 181 files / ran=3994 / 0 failures, all matrix legs green; local full suite 182 files / 4149 tests green; ruff clean; codex impl-review SHIP.
## Evidence
- Commits: 9b8073efdd5e2baa2ea6f08ab31b1a3d2a68053b, 0946216fa0e2a719a909b1c2524aa241f15a3fff, ec437e87a7c1a23cca3f59cb102f3b20a09f5b01
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_normalize_section_content test_task_create_files -q (local, baseline green 54 tests; post-fix 56 tests OK skipped=1), python3 scripts/run_tests_parallel.py (local full: files=182 ran=4149 failures=0 errors=0 skipped=5, wall=676s; green receipt ec437e87-unittest), uvx ruff@0.16.0 check . (clean), windows-latest focused @ 9b8073ef: run 30913388943 SUCCESS test_normalize_section_content.py PASS ran=28 skipped=0 (real 8.3 short-path case RAN, not skipped), windows-latest focused @ 9b8073ef: run 30913412784 SUCCESS test_task_create_files.py PASS ran=28 skipped=1 (only the POSIX chmod-000 premise skipped), windows-latest focused @ 9b8073ef: run 30913423957 FAILURE test_run_tests_parallel.py - evidence that a Windows child's OWN unittest stream is cp1252 (message mangled before the pipe); drove the runner-change revert, windows-latest focused @ 0946216f: run 30914459018 SUCCESS test_run_tests_parallel.py PASS ran=20, windows-latest full parallel @ 0946216f: run 30915298985 SUCCESS - Windows 181 files ran=3996 failures=0 errors=0 skipped=82; all matrix legs green, windows-latest full parallel @ ec437e87 (final SHA): run 30917819145 SUCCESS - Windows 181 files ran=3994 failures=0 errors=0 skipped=82 wall=578s, only test_backend_spec.py still excluded (fn-120.3); ubuntu 3.11/3.x, macos, windows-python3-stub, py3.12/3.13 smokes all green, run URLs: https://github.com/gmickel/flow-next/actions/runs/<id> for ids 30913388943 30913412784 30913423957 30914459018 30915298985 30917819145, baseline: green (pre-edit focused Quick command, 54 tests OK)
- PRs:
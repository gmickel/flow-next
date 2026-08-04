---
satisfies: [R1, R2, R3, R7, R10, R11, R13]
---
# fn-120-windows-test-corpus-compatibility-sweep.1 Fix deterministic Windows encoding, shim, and path portability

## Description
Characterize all six exclusions on current Windows HEAD, establish permanent exact-ref diagnostic inputs, then clear the three deterministic portability failures with real CI evidence.

**Size:** L
**Files:** .github/workflows/test-flow-next.yml, plugins/flow-next/tests/test_flow_gitignore.py, plugins/flow-next/tests/test_gate_receipt.py, plugins/flow-next/tests/test_reveval_parse_guard.py, plugins/flow-next/scripts/flowctl.py only if production audit finds a real bug

### Approach

First run every excluded file separately on current `windows-latest`, before changes, and record exact current failure data. Add permanent validated `workflow_dispatch` inputs for exact-ref `suite_mode` (parallel/serial/shuffle), optional one-file pattern, verbosity, and bounded timeout; ordinary PR/push behavior remains unchanged.

Then make controlled gitignore reads explicitly UTF-8 and verify production writes/reads. Split the gate-receipt fixture along the real platform boundary: a reasoned POSIX-only skip for literal-backslash filename creation, plus an injectable status-call seam or actual Windows executable wrapper for TTL behavior; assert the double actually ran. Replace reveval string path derivation with resolved `pathlib` paths and retain the end-to-end subprocess test.

Run each fixed file alone on `windows-latest` before the combined full runner. Remove each exclusion only in the same commit as its fix; record the green workflow run and `headSha`.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_flow_gitignore test_gate_receipt test_reveval_parse_guard -q
```

## Acceptance
- [ ] A pre-fix current-HEAD Windows run characterizes all six files with current corpus count, test names/counts, tracebacks, elapsed time, exits, and child-process observations.
- [ ] Permanent `workflow_dispatch` inputs reproduce parallel/serial/shuffle or one-file verbose bounded runs on an exact ref; run evidence records `headSha`.
- [ ] Controlled text I/O is explicit UTF-8; the en-dash roundtrip passes on Windows without locale fallback.
- [ ] Only the impossible literal-backslash filename premise is POSIX-skipped; TTL/receipt behavior uses a proven seam/executable and asserts the delayed/failing double ran.
- [ ] Reveval guard resolves repo paths portably and its real subprocess path passes on Windows.
- [ ] All three files are removed from `EXCLUDES` in the same commit as fixes/regressions.
- [ ] Focused and combined `windows-latest` runs are green and their run URL/ID plus `headSha` is recorded in task evidence.
- [ ] Linux/macOS focused regressions remain green; no assertion is weakened.

## Done summary
Cleared the three deterministic Windows portability failures (fn-120 R1/R2/R3) with real windows-latest CI evidence, after adding permanent validated workflow_dispatch diagnostics (suite_mode=parallel|serial|shuffle, single-file pattern, verbose, bounded file_timeout 1-900s; an explicit pattern bypasses the Windows EXCLUDES so focused runs can reach excluded files; push/PR behavior unchanged) and a full six-file pre-fix characterization on current HEAD (R13).

Characterization @ 930cd764 (runs 30902967690..30902994209, serial verbose, file_timeout=300):
- test_backend_spec.py: PASS ran=155 in 4.40s — the 900s hang does NOT reproduce on the current windows-2025 runner image (fn-120.3 owns retirement + cleanup regression).
- test_flow_gitignore.py: FAIL ran=8 f=2 e=1 — bare read_text/write_text decoded UTF-8 em dash as cp1252 (0x97 UnicodeDecodeError / mojibake). Production _ensure_flow_gitignore audited: already explicit UTF-8 everywhere; fixture-only bug, no flowctl.py change needed.
- test_gate_receipt.py: FAIL ran=49 f=1 e=1 skip=4 — literal-backslash filename premise impossible on NT (FileNotFoundError); #!/bin/sh git shim never executed by shell=False CreateProcess, so the almost-stale receipt was wrongly HONORED.
- test_reveval_parse_guard.py: FAIL ran=2 e=1 — NOT a path failure on current HEAD: guard's print() of a U+2192 check label raised UnicodeEncodeError on cp1252 stdout.
- test_normalize_section_content.py: FAIL ran=26 f=2 — flowctl --acceptance-file/--file from 8.3 short paths (RUNNER~1) exit 1 (fn-120.2 scope).
- test_task_create_files.py: import ERROR — unguarded os.geteuid() at class body (fn-120.2 scope; confirms spec R5's suspicion, not 8.3 paths).

Fixes (each exclusion removed in the same commit as its fix, R7):
- 7fc6892f test_flow_gitignore: explicit UTF-8 on all test I/O + non-ASCII roundtrip assertion.
- 13f141c9 test_gate_receipt: injectable asserted git-status seam (patch module subprocess.run; delegates non-status calls; proves the delayed/failing double ran) replaces the PATH shim for the TTL race AND unskips the git-status-failure exit-2 case; only the literal-backslash filename premise keeps a narrowly reasoned skipUnless(os.name=="posix"); Windows-valid lookalike coverage retained.
- f03dfb83 test_reveval_parse_guard: pathlib parents/joinpath derivation (no dirname chains/string separators), ASCII-by-construction guard check labels (content assertions untouched), new standalone-subprocess e2e case pinning the cp1252 stdout regression.

Proof @ f03dfb83: focused windows-latest runs 30904236477 (gitignore ran=8), 30904241024 (gate_receipt ran=49 skip=4), 30904245155 (reveval ran=3) all SUCCESS; combined full run 30904249464 SUCCESS — Windows 179 files ran=3938 f=0 e=0, ubuntu/macos legs green, no assertion weakened. Local focused suite green (60 tests), full ruff clean, green receipt f03dfb83-unittest.

Plan-sync note for fn-120.2/.3: fresh characterization supersedes the 2026-07-20 signatures — backend_spec currently passes in 4.4s, and reveval's failure was stdout encoding, not path resolution.
## Evidence
- Commits: 930cd764ffbafd555534a1641cebcbcd7b1c25b6, 7fc6892f318ab34815ab0c1627e030df4e633460, 13f141c9e8218883b35c196453d7e8c7a73518ef, f03dfb83390d22e65db2c5c4a10c3f2b30c21b20
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_flow_gitignore test_gate_receipt test_reveval_parse_guard -q (local, 60 tests, OK skipped=1), uvx ruff@0.16.0 check . (clean), windows-latest pre-fix characterization @ 930cd764 (all six excluded files, serial verbose file_timeout=300): test_backend_spec.py run 30902967690 PASS ran=155 4.40s (no hang on windows-2025 image); test_flow_gitignore.py run 30902973015 FAIL ran=8 failures=2 errors=1 1.11s (bare read_text/write_text cp1252 vs UTF-8 em dash, UnicodeDecodeError 0x97); test_gate_receipt.py run 30902978400 FAIL ran=49 failures=1 errors=1 skipped=4 12.65s (literal-backslash filename FileNotFoundError; #!/bin/sh TTL shim never executed -> stale receipt HONORED); test_normalize_section_content.py run 30902984009 FAIL ran=26 failures=2 3.74s (8.3 short-path RUNNER~1 --acceptance-file/--file args exit 1); test_reveval_parse_guard.py run 30902989217 FAIL ran=2 errors=1 2.09s (UnicodeEncodeError U+2192 printing check label to cp1252 stdout - NOT a path failure on current HEAD); test_task_create_files.py run 30902994209 ERROR import 1.45s (unguarded os.geteuid() AttributeError at class body line 343), windows-latest focused proof @ f03dfb83390d22e65db2c5c4a10c3f2b30c21b20: test_flow_gitignore.py run 30904236477 SUCCESS PASS ran=8; test_gate_receipt.py run 30904241024 SUCCESS PASS ran=49 skipped=4; test_reveval_parse_guard.py run 30904245155 SUCCESS PASS ran=3 (incl. new standalone subprocess e2e), windows-latest combined full parallel @ f03dfb83390d22e65db2c5c4a10c3f2b30c21b20: run 30904249464 SUCCESS - Windows leg 179 files (182 discovered - 3 remaining excludes), ran=3938 failures=0 errors=0 skipped=81 wall=565s jobs=4; all matrix legs green (ubuntu 3.11/3.x, macos, windows, windows-python3-stub, py3.12/3.13 smokes), run URLs: https://github.com/gmickel/flow-next/actions/runs/<id> for ids 30902967690 30902973015 30902978400 30902984009 30902989217 30902994209 30904236477 30904241024 30904245155 30904249464
- PRs:
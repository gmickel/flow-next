# fn-120 Windows test-corpus compatibility sweep

## Goal & Context
<!-- scope: business -->

The main Flow-Next test workflow runs 81 of 87 Python test files on `windows-latest`. Six files remain explicitly excluded after fn-119 first expanded Windows from a small smoke subset to nearly the whole corpus. Those exclusions are visible debt against the project's three-OS compatibility promise: a change can pass Linux/macOS and still regress production behavior or test infrastructure hidden behind the Windows filter.

This spec makes all behaviorally portable tests run on Windows and empties the Windows-only exclusion list. Fixes must preserve assertion strength. A POSIX-impossible fixture may retain a narrowly documented platform skip only when the same product behavior has a Windows-native equivalent test.

The execution order is evidence-driven. Known deterministic portability bugs land first; path failures are reproduced with real Windows short paths before remediation; the 900-second backend-spec hang is isolated last with bounded diagnostics and process cleanup. Every exclusion is removed only with a real green `windows-latest` run on the same commit.

## Architecture & Data Models
<!-- scope: technical -->

### Current truth surface

`.github/workflows/test-flow-next.yml` constructs a Windows-only `EXCLUDES` array passed to `scripts/run_tests_parallel.py --exclude`. The original fn-119 baseline was 81/87 files, but current HEAD discovers 118 test files and runs 112/118 after exclusions. Counts and failure signatures are therefore characterization inputs, not frozen truth. Task 1 must run all six files on current `windows-latest` before remediation and update the evidence table with test names/counts, full tracebacks, elapsed time, exit status, and observed child processes.

The runner already supports:

- one-file isolation through `--pattern`;
- deterministic `--serial`;
- bounded per-file execution via `--file-timeout`;
- explicit reporting of every excluded file.

Those are the diagnostic primitives. This spec does not replace the runner or create a second Windows harness.

The six owners and observed first-run failures are:

| File | Observed Windows failure | Initial remediation direction |
|---|---|---|
| `test_flow_gitignore.py` | cp1252 readback/mojibake of UTF-8 en dash | explicit UTF-8 test reads; audit production writes |
| `test_gate_receipt.py` | literal backslash filename impossible on NT; `/bin/sh` git shim cannot execute | narrow POSIX skip for impossible filename premise plus an asserted injectable status-call seam or actual Windows executable wrapper |
| `test_reveval_parse_guard.py` | end-to-end guard path resolution error | use `pathlib.Path` repo-root derivation and preserve real subprocess path |
| `test_normalize_section_content.py` | CLI file arguments fail from 8.3 temp paths | reproduce on actual Windows short path, then fix common production/harness cause |
| `test_task_create_files.py` | one error, suspected but unproven relation to short paths | isolate independently; share fix with normalize only if evidence proves one cause |
| `test_backend_spec.py` | file exceeds 900-second timeout | per-test verbose/bounded isolation, identify waiting subprocess/handle, add cleanup regression |

All six pass locally on POSIX (258 tests with one expected POSIX-specific skip), so only Windows CI can close the acceptance criteria.

### Remediation layers

Fix the narrowest truthful layer:

1. **Test portability** when production already uses a portable contract and the fixture assumes POSIX/default encoding.
2. **Production portability** when the real `flowctl` behavior fails for valid Windows paths, encodings, shells, or subprocess lifecycles.
3. **Platform-specific fixture adapter** when the behavior is portable but the fake executable format differs (`.cmd` instead of `#!/bin/sh`).
4. **Narrow skip** only for a premise Windows cannot represent (a filename containing literal `\`). The skip reason must name that impossibility; adjacent behavior remains tested through a Windows-valid case.

No assertion deletion, expected-error broadening, timeout inflation, or silent exclusion counts as remediation.

### CI proof loop

For each task:

1. Extend `workflow_dispatch` permanently with validated inputs: `suite_mode=parallel|serial|shuffle`, optional single-file `pattern`, `verbose`, and bounded `file_timeout`. Ordinary PR/push behavior remains unchanged. Use `gh workflow run --ref <branch>` and record the resulting run's `headSha`.
2. Capture the exact failing test, traceback/stdout/stderr, elapsed time, and process exit.
3. Implement the smallest fix plus a regression assertion.
4. Remove that file from the workflow `EXCLUDES` array in the same commit.
5. Push and require a green `windows-latest` run for the commit. Record workflow run URL/ID in Flow task evidence.
6. If the run remains red or hangs, the exclusion stays. Iterate without weakening the gate.

Permanent manual inputs remain because they are the reproducible compatibility diagnostic surface. Temporary logging beyond those inputs is removed before task completion unless it materially improves bounded hang observability.

### Final corpus gate

After the final exclusion is removed:

- the workflow contains no Windows `EXCLUDES` entries;
- `python3 scripts/run_tests_parallel.py` passes on `windows-latest`;
- `python3 scripts/run_tests_parallel.py --serial` passes on `windows-latest`;
- one shuffled/order-varied run passes to catch hidden file-order/process leakage;
- per-file timeouts remain bounded and diagnostic;
- Linux and macOS full gates remain green.

No new persistent data model or public CLI surface is introduced.

## API Contracts
<!-- scope: technical -->

Production CLI behavior preserved or clarified by tests:

- All repository-controlled text files read/written by Flow-Next use UTF-8 explicitly.
- Valid Windows absolute paths, including paths represented in 8.3 short form and paths containing spaces, work for `flowctl ... --file <path>` commands.
- Gate-receipt TTL tests invoke a proven test seam or actual executable wrapper and assert that the delayed/failing double ran; a PATH-preceding `.cmd` alone is insufficient because production uses `subprocess.run([...], shell=False)`.
- Review/backend subprocesses never require interactive stdin in tests, close inherited pipes/handles, terminate their process tree on timeout, and return within the runner's bounded per-file timeout.
- Path derivation uses `pathlib`/resolved filesystem paths rather than string splitting on `/` or assumptions about drive-letter casing.

CI contract:

```yaml
# Windows runs the same discovered Python test corpus as Linux/macOS.
# No Windows-only EXCLUDES array remains.
```

The full runner's existing flags and output schema remain backward-compatible.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Real Windows proof required.** Local Wine, POSIX simulation, mocked `os.name`, or a unit-only green run cannot remove an exclusion.
- **Real short paths required.** The 8.3 failures must be reproduced using a Windows volume/path where a short name actually exists. If CI has 8.3 generation disabled, use a path fixture that demonstrates the observed `RUNNER~1` form from the failing run or provision a deterministic Windows workspace that exposes it; do not merely replace slashes in a string.
- **Encoding strictness.** Specify `encoding="utf-8"` on controlled text I/O; do not use locale fallbacks or replacement decoding.
- **Literal backslash filename.** `\` is a Windows separator and cannot be a filename character. The exact filesystem premise may be `skipUnless(os.name == "posix")`, but the receipt/path-safety behavior it protects must have a Windows-valid equivalent assertion.
- **Timeouts are signals.** Do not raise the 900-second timeout to mask `test_backend_spec.py`. Reduce isolated diagnostic timeouts where useful and guarantee child cleanup.
- **Process trees.** Windows child termination differs from POSIX process groups. `scripts/run_tests_parallel.py` must explicitly launch isolated process trees/groups, close stdin, terminate descendants on timeout, bound post-kill collection, and prove no orphaned `git`, shell, Codex/Copilot/backend double, or Python process holds a pipe/lock.
- **Test independence.** Full, serial, and shuffled runs must pass; no test may rely on execution order, inherited environment mutation, or a prior test's temp directory.
- **Same-commit removal.** Workflow exclusion and fix/regression test are atomic. Reverting the fix must make the now-included test fail.
- **No compatibility downgrade.** Linux/macOS assertions and timeouts remain at least as strong.
- **Coordination.** Avoid concurrent implementation with fn-122 if both touch `flowctl.py` or backend process code.
- **Version discipline.** Add `## Unreleased` changelog entry; no version bump. This is compatibility/test debt, not a new public command.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `test_flow_gitignore.py` uses explicit UTF-8 for controlled reads; production Flow gitignore I/O is verified explicit UTF-8; the test is removed from Windows exclusions with same-commit regression coverage and a green Windows run.
- **R2:** `test_gate_receipt.py` retains at most a narrowly reasoned POSIX skip for the impossible literal-backslash filename and uses an asserted status-call seam or actual Windows executable wrapper for the TTL race; the double's invocation is proven, the file runs green on Windows, and it leaves the exclusion list.
- **R3:** `test_reveval_parse_guard.py` derives repository/executable paths portably and passes its real end-to-end guard on Windows; no string-separator or drive-letter assumption remains.
- **R4:** `test_normalize_section_content.py` reproduces the valid Windows 8.3-path failure and passes after the narrow production or harness fix; its exclusion is removed only with green Windows evidence.
- **R5:** `test_task_create_files.py` is independently isolated; current evidence points to unguarded `os.geteuid()` rather than 8.3 paths, so the POSIX permission premise is guarded while all portable assertions remain active unless fresh Windows characterization proves another cause.
- **R6:** `test_backend_spec.py` completes below the existing bounded file timeout on Windows; a regression test covers the identified wait/handle/process-tree cause and proves cleanup on success and timeout.
- **R7:** Every exclusion removal lands in the same commit as its fix and focused regression; each task records the exact green `windows-latest` workflow run URL/ID in Flow evidence.
- **R8:** The final workflow contains no Windows-only `EXCLUDES` list or six-file compatibility exception; the runner reports zero skipped files due to workflow filtering.
- **R9:** Full parallel, full serial, and shuffled/order-varied corpus runs pass on `windows-latest`, while Linux and macOS full gates remain green.
- **R10:** Assertions are not weakened: no broad exception catches, locale fallback decoding, blanket Windows skip, disabled timeout, or increased hang ceiling.
- **R11:** Permanent workflow-dispatch inputs can reproduce focused/serial/shuffled runs on an exact ref, and runner diagnostics identify timed-out file, elapsed time, exit code, and captured output; a synthetic grandchild-holds-stdout regression proves POSIX process-group and Windows process-tree cleanup with bounded post-kill collection.
- **R12:** Repository CHANGELOG records complete Windows corpus parity under `## Unreleased`; no public docs or version manifests change unless a real user-visible portability bug requires documentation.
- **R13:** Before any exclusion fix, a current-HEAD `windows-latest` characterization runs all six files and records discovered corpus counts plus per-file test names/counts, tracebacks, elapsed time, exit status, and observed child processes; remediation follows that evidence rather than the 2026-07-20 signatures.

## Boundaries
<!-- scope: business -->

Out of scope:

- Rewriting the parallel test runner or changing its discovery model.
- Supporting Python versions, Windows editions, or shells outside the existing CI support matrix.
- Making POSIX-impossible filesystem semantics exist on Windows.
- Broad path/encoding refactors unrelated to a captured failure.
- Relaxing assertions, replacing end-to-end coverage with mocks, or permanently excluding slow files.
- Expanding Windows CI into packaging/installer coverage.
- Public docs-site work unless a production CLI behavior changes.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

Three-OS support is only credible when the same behavioral corpus runs everywhere. fn-119 made the debt measurable instead of silently running a small Windows subset; fn-120 pays the remaining bounded debt and turns exclusions from an indefinite escape hatch into temporary, evidence-owned exceptions.

### Implementation Tradeoffs
<!-- scope: technical -->

**Decisions frozen 2026-07-23:**

1. **Actual CI is the acceptance surface.** The failures are Windows-specific and several involve filesystem/subprocess semantics. No local approximation can close them.
2. **Small known fixes before the hang.** Removing deterministic encoding/path/shim issues increases signal and keeps the backend hang investigation isolated.
3. **One exclusion, one proven owner.** `test_normalize_section_content.py` and `test_task_create_files.py` may share a cause, but the plan does not assume it.
4. **Skip the impossible premise, not the behavior.** Literal `\` filenames are POSIX-only; receipt safety and TTL race behavior remain cross-platform.
5. **Bound and diagnose hangs.** A higher timeout would hide leaked handles or interactive waits. Permanent diagnostics and cleanup are part of the fix.
6. **Same-commit gate removal.** This preserves bisectability and prevents a period where CI is either falsely green or knowingly broken.

Rejected: removing all exclusions first and debugging a red matrix; increasing timeouts; locale-dependent decoding; mocking short paths; blanket `@skipIf(os.name == "nt")`; treating local POSIX green as proof.

## Investigation Targets

- `.github/workflows/test-flow-next.yml` Windows `EXCLUDES` block and matrix commands.
- `scripts/run_tests_parallel.py` pattern, serial, timeout, output capture, and process cleanup.
- `plugins/flow-next/tests/test_backend_spec.py` subprocess/backend integration cases.
- `plugins/flow-next/tests/test_flow_gitignore.py` controlled text reads.
- `plugins/flow-next/tests/test_gate_receipt.py` literal-backslash and TTL-shim fixtures.
- `plugins/flow-next/tests/test_normalize_section_content.py` CLI `--file` fixtures.
- `plugins/flow-next/tests/test_reveval_parse_guard.py` repo-root and guard invocation.
- `plugins/flow-next/tests/test_task_create_files.py` isolated failing case.
- `plugins/flow-next/scripts/flowctl.py` gitignore I/O, file-argument normalization, backend subprocess helpers.
- GitHub Actions run `29754617049` / fn-119 PR #219 as original failure evidence.

## Task Breakdown

1. **Deterministic portability fixes** — UTF-8 gitignore reads, Windows-native gate-receipt fixture with narrow POSIX-only filename skip, and portable reveval path derivation; remove those three exclusions with focused Windows proof.
2. **Path portability remediation** — reproduce real 8.3 behavior for normalize; independently fix task-create's evidenced Windows portability cause (currently `os.geteuid()`), sharing a fix only if fresh evidence proves one.
3. **Backend hang and runner cleanup** — capture the exact hanging test/process, fix cleanup/wait semantics, add synthetic descendant-cleanup coverage, and remove the last exclusion.
4. **Zero-exclusion final matrix** — prove parallel/serial/shuffled full-corpus parity on the exact final SHA across all OSes and update CHANGELOG.

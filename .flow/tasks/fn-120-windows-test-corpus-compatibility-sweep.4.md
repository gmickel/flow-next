---
satisfies: [R8, R9, R12]
---
# fn-120-windows-test-corpus-compatibility-sweep.4 Prove final zero-exclusion Windows corpus matrix

## Description
Prove the final zero-exclusion corpus in parallel, serial, and shuffled modes across the supported OS matrix and record the compatibility result.

**Size:** M
**Files:** .github/workflows/test-flow-next.yml only if final proof exposes a matrix bug, scripts/run_tests_parallel.py only if proof exposes an order-mode bug, CHANGELOG.md, plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py (leaf_is_safe flake fix owed by the fn-120.3 handover, see Approach note), plugins/flow-next/tests/test_tracker_capabilities.py (regression)

### Approach

On the exact final candidate SHA, run `windows-latest` through the permanent workflow-dispatch inputs in full parallel, full serial, and shuffled/order-varied modes. Require zero workflow-filtered files. Run Linux and macOS full gates on the same SHA. Record every run URL/ID and `headSha`, remove temporary probes, retain the permanent bounded diagnostic inputs, and add an `## Unreleased` changelog entry with no version bump.

<!-- Updated by plan-sync: fn-120.3 (final SHA deceb99a, run 30928443192) already produced a green full-parallel windows-latest proof (182 files / ran=4165 / 0 failures / zero exclusions) plus green Linux/macOS on the same commit -- that satisfies this task's parallel leg and same-SHA Linux/macOS requirement if deceb99a remains the final candidate; this task still owes the SERIAL and SHUFFLED/order-varied legs (and re-running parallel if the flake fix below moves the candidate SHA). Do not re-derive the parallel proof from scratch, but do not skip it either -- cite fn-120.3's run as the parallel evidence. -->

<!-- Updated by plan-sync: HANDOVER from fn-120.3 (owns R9) -- a pre-existing ~50% Windows flake in `test_tracker_capabilities.test_concurrent_relates_lose_no_ledger_entry` was observed (run 30921678923 RED, identical re-run 30923544649 GREEN) and is NOT related to this spec's exclusion work, but it MUST be fixed first: R9's parallel/serial/shuffled zero-exclusion proof cannot be trusted while a flaky failure can turn a real run red. Signature: `leaf_is_safe` in `plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py` resolves base and leaf independently; Windows non-strict `Path.resolve()` can stop expanding on a transient error under concurrent writers, producing a false "<leaf> escapes <base>" `INVALID_INPUT` on a barrier-driven double `relate` into `.flow/create-first/`. Fix direction: derive the leaf from the already-resolved base instead of resolving both independently. Because the fix touches `flowctl_tracker/lifecycle/helpers.py`, it requires the propagation chain per CLAUDE.md: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`, `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`, `python3 scripts/gen_tracker_manifest.py`, then `./scripts/sync-codex.sh` twice. Land this fix (with its own regression) before treating any R9 proof run as final. -->

### Quick commands

```bash
python3 scripts/run_tests_parallel.py
python3 scripts/run_tests_parallel.py --serial
python3 scripts/run_tests_parallel.py --shuffle --seed 120
```

## Acceptance
- [ ] Exact-SHA Windows full parallel, full serial, and shuffled/order-varied runs pass with zero workflow-filtered files.
- [ ] Linux and macOS full gates pass on the same final SHA.
- [ ] Every proof records workflow URL/ID plus `headSha`; run heads match the candidate commit.
- [ ] Workflow contains no Windows `EXCLUDES` block and runner list-only confirms the complete current corpus.
- [ ] Temporary diagnostics are removed; permanent manual diagnostic inputs and bounded cleanup diagnostics remain.
- [ ] CHANGELOG contains an `## Unreleased` Windows corpus parity entry; no version manifest or public docs change.


## R9 matrix proof (final candidate a58d5165)

Final CODE candidate SHA: `a58d516552e5f17b237e287f9be5aae08c56d4f4` (`a58d5165`, the
`leaf_is_safe` flake fix owed by the fn-120.3 handover). Every leg below ran
`workflow_dispatch` on `--ref fn-120-windows-test-corpus-compatibility-sweep` with
`headSha == a58d5165` — verified per run, not inferred. Each dispatch runs the WHOLE
OS matrix, so Windows/Linux/macOS in a row are the same commit by construction.
fn-120.3's `deceb99a` parallel proof is superseded (SHA moved), not cited.

| Mode | Run ID | URL | headSha | windows-latest | ubuntu 3.11 / 3.x | macos-latest |
|---|---|---|---|---|---|---|
| parallel | 30934798637 | https://github.com/gmickel/flow-next/actions/runs/30934798637 | a58d5165 | success — `files=182 ran=4170 failures=0 errors=0 skipped=82 wall=611.48s jobs=4` | success / success | success |
| serial | 30934815997 | https://github.com/gmickel/flow-next/actions/runs/30934815997 | a58d5165 | success — `files=182 ran=4170 failures=0 errors=0 skipped=82 wall=1339.49s jobs=1` | success / success | success |
| shuffle | 30934833655 | https://github.com/gmickel/flow-next/actions/runs/30934833655 | a58d5165 | success — `shuffle: on (seed=30934833655)`, `files=182 ran=4170 failures=0 errors=0 skipped=82 wall=615.13s jobs=4` | success / success | success |

All three runs: `conclusion == success` for the whole matrix (including the Python
3.12/3.13 compatibility smokes and `windows-python3-stub`).

Zero workflow-filtered files: the workflow has no Windows `EXCLUDES` block (the
`run_tests_parallel.py` invocation takes no per-OS filter — see the standing
"never re-add a per-OS filter here" comment), and `files=182` on the Windows leg
equals the complete discovered corpus — `run_tests_parallel.py --list-only` emits
182 files locally, matching `ls plugins/flow-next/tests/test_*.py | wc -l` = 182.
`skipped=82` are in-test `skipUnless` skips (the Windows-invalid-filename case and
POSIX-only assertions), not corpus exclusions; the same 182 files execute on
every OS.

Temporary diagnostics: none left. The workflow retains only the PERMANENT
`workflow_dispatch` inputs (`suite_mode` parallel|serial|shuffle, `pattern`,
`verbose`, `file_timeout` 1-900, `legacy_baseline`) and the permanent 9009-stub /
`pick_python_test.sh` probe regressions; all are inert on push/pull_request.

Records-commit note: the flow-record commit that carries this proof touches only
`.flow/` task/spec records — no path in the workflow's `push`/`pull_request`
filters and no file the suite reads — so it cannot invalidate the proof above.
`a58d5165` remains the final code candidate.

## Done summary
Proved the final zero-exclusion Windows corpus at candidate SHA `a58d5165` — `windows-latest` ran the complete 182-file / 4170-test corpus green in parallel (run 30934798637), full serial (30934815997), and shuffled order (30934833655, seed=30934833655), with the same-SHA ubuntu-3.11 / ubuntu-3.x / macos-latest legs and the Python 3.12/3.13 + 9009-stub smokes green in every run; every run's `headSha` was verified equal to `a58d516552e5f17b237e287f9be5aae08c56d4f4`, so fn-120.3's superseded `deceb99a` parallel proof is not cited.

The proof was unblocked by first landing the flake fix the fn-120.3 handover owed: `leaf_is_safe` resolved base and leaf independently, and Windows' non-strict `Path.resolve()` can stop expanding under concurrent writers, so two spellings of the same directory (8.3 `RUNNER~1` vs expanded) compared unequal and faked an "escapes" `INVALID_INPUT` (~50% flake). Containment is now derived from one resolve plus a lexical `..` check, with the no-follow symlink refusal unchanged and a five-case regression class (`LeafIsSafeDivergentResolve`) that patches a divergent resolve and keeps the escape/symlink teeth. The workflow still carries no Windows `EXCLUDES`, `--list-only` confirms all 182 discovered files run (the 82 Windows skips are in-test `skipUnless`, not corpus filtering), only the permanent bounded `workflow_dispatch` diagnostics remain, and CHANGELOG has the `## Unreleased` parity entry with no version bump.
## Evidence
- Commits: a58d516552e5f17b237e287f9be5aae08c56d4f4, f46e94706c7c81ff1dba73e98ca8771c2f09212d, 6afd156d4771ac9e33cdda43f5907d796c3ed0b4
- Tests: python3 scripts/run_tests_parallel.py (local, final tree: files=182 ran=4170 failures=0 errors=0 skipped=5), uvx ruff@0.16.0 check . (All checks passed), python3 scripts/run_tests_parallel.py --list-only (182 files == ls plugins/flow-next/tests/test_*.py | wc -l == 182, zero corpus exclusions), CI run 30934798637 parallel @ headSha a58d516552e5f17b237e287f9be5aae08c56d4f4 - windows-latest files=182 ran=4170 failures=0 errors=0 skipped=82; ubuntu 3.11+3.x, macos-latest all success - https://github.com/gmickel/flow-next/actions/runs/30934798637, CI run 30934815997 serial @ headSha a58d516552e5f17b237e287f9be5aae08c56d4f4 - windows-latest files=182 ran=4170 failures=0 errors=0 skipped=82 jobs=1; ubuntu 3.11+3.x, macos-latest all success - https://github.com/gmickel/flow-next/actions/runs/30934815997, CI run 30934833655 shuffle (seed=30934833655) @ headSha a58d516552e5f17b237e287f9be5aae08c56d4f4 - windows-latest files=182 ran=4170 failures=0 errors=0 skipped=82; ubuntu 3.11+3.x, macos-latest all success - https://github.com/gmickel/flow-next/actions/runs/30934833655, propagation chain re-run clean: rsync flowctl_tracker -> .flow/bin, gen_tracker_manifest.py, sync-codex.sh twice (no diff); test_tracker_distribution green in suite, codex impl-review (gpt-5.6-sol, base cd8490fe): round 1 NEEDS_WORK (missing final-SHA proof) -> round 2 SHIP, 0 unaddressed R-IDs; receipt /tmp/impl-review-receipt-fn-120-windows-test-corpus-compatibility-sweep.4.json, session 019fcde4-04e8-79c0-b80b-3f8ec4ec7be6, baseline: green (pre-edit state was the committed a58d5165 tree; gate classify --base cd8490fe = FULL, full gates run), green receipt: .flow/tmp/green-receipts/f46e9470-unittest.json
- PRs:
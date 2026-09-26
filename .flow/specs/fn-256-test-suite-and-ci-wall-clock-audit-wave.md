# Test suite and CI wall-clock (audit wave 2)

## Goal & Context
<!-- Goal & Context: 70% [paraphrase], 30% [inferred] -->

Every flow-next spec pays the full unit gate at least once locally and three times in CI (ubuntu, macOS, Windows). The 2026-09-24 efficiency audit measured where that time goes. Roughly 77% of summed per-file suite time is flowctl subprocesses, and about 240 ms of each ~330 ms spawn is CPython recompiling the ~57K-line `flowctl.py`. A file run as `__main__` never gets bytecode-cached, while an imported module does. Git fixture setup is negligible (~37 ms per bare+clone+commit+push).

Measured baselines: local full suite 234 s (critical path `test_spec_chain.py`). CI units: ubuntu ~578 s, macOS ~912 s, Windows ~966-1054 s. The Windows units job is the PR's critical path, and median PR CI is about 15.4 min.

This wave makes the developer loop cheaper for every later wave. It also closes two gate holes the audit found: skill-only edits skip the smokes that check skill markdown, and nothing in CI checks that the generated Codex mirror is fresh. R8 is diagnosis only.

## Architecture & Data Models

- **Test-side flowctl entry.** A shared test support module exposes the argv the tests use to spawn flowctl. It is a tiny runner script that puts the flowctl scripts directory on `sys.path`, imports `flowctl`, sets `sys.argv[0]` to the script path (argparse derives its program name from it), and calls `flowctl.main()`. Tests keep process isolation, exit codes, stdout/stderr and env behavior. Only the compile cost changes, because the imported module's bytecode is cached in the already git-ignored `__pycache__/`.
- **Runner scheduling.** `run_tests_parallel.py` submits files to its pool largest-first by file size. The printed summary and `--list-only` output keep today's order. `--shuffle` keeps its seeded order.
- **Shared initialized fixture.** Test classes that repeat `init` / `config set` / `memory init` per test build one initialized repo per class and copy it per test.
- **Codex mirror check.** `sync-codex.sh` gains a check mode that builds into a temporary directory and compares it with the committed mirror (including the tracker manifest check). CI runs it.

## Edge Cases & Constraints

- Module-level caches in flowctl keyed on cwd (`_SPEC_BASE_CACHE`, `_REPO_ROOT_CACHE`, `_STATE_DIR_CACHE`) are irrelevant to the subprocess runner, since each spawn is still a fresh process. The runner must not become an in-process `main()` call in this wave.
- Tests that deliberately scrub `env` (for example the ConsumerWorld shim) must still reach the runner with the same env they pass today.
- `__pycache__/` is already git-ignored. A warm run must leave the working tree clean, because green-receipt cleanliness probes depend on it.
- On a read-only or unwritable scripts directory, CPython silently skips writing bytecode. Tests still pass and are just not accelerated.
- Windows: the runner path must work under the Windows unit leg (same interpreter as the test process, no shebang reliance).

## Acceptance Criteria

- **R1:** Test files that spawn `flowctl.py` as a script go through one shared test-support runner that imports the flowctl module and calls its `main()`. `test_startup_bootstrap.py` and `test_bin_launcher_parity.py` keep exercising the real product entry points. The runner sets `sys.argv[0]` to the flowctl script path before calling `main()`, so usage, help and error text stay byte-identical to a script run. Full-suite results are unchanged (same pass/skip counts), and the task receipt records local suite wall time before and after on the same machine. Errors: a test that needs the real script entry (launcher/bootstrap parity) opts out explicitly and stays on it; a missing runner file fails loudly with a path in the error, never a silent fallback. [paraphrase]
- **R2:** `run_tests_parallel.py` submits files to its worker pool in descending file-size order. The printed per-file summary, `--list-only` output and `--shuffle`/`--seed` behavior are unchanged, and a runner test pins that submission order. Errors: no error surface beyond today's discovery errors. [paraphrase]
- **R3:** Test classes that repeat the `init` + `config set` + `memory init` sequence per test (at least the memory core and memory marks suites) build one initialized repo per class and copy it per test. Each test still gets an isolated repo that no other test mutates. Errors: a copy failure fails the test with its path, never reuses a mutated template. [paraphrase]
- **R4:** A change that touches only skill or agent markdown under the plugin selects the functional smokes in CI. Either the changes classifier treats plugin `skills/**` and `agents/**` markdown as smoke-relevant, or the behavioral skill-markdown assertions move from the smoke scripts into the unit suite and the prose greps are deleted (G2). A classifier test covers a skill-only change. Errors: no error surface beyond the classifier's existing full-run fallback. [paraphrase]
- **R5:** `sync-codex.sh --check` regenerates the Codex mirror into a temporary directory and exits non-zero with a diff summary when the committed mirror differs, without modifying the working tree. It also runs the tracker manifest generator in its check mode. CI's ubuntu units job runs it. The developer policy's "run sync-codex twice" instruction becomes "run once; CI enforces freshness". Errors: a stale mirror fails CI with the differing paths listed; a generator error fails the check with its output. [paraphrase]
- **R6:** The impl-review smoke runs the Ralph smoke sweep once instead of under four `FLOW_VALIDATE_REVIEW`/`FLOW_REVIEW_DEEP` combinations, because nothing the Ralph smoke exercises reads those variables. The env-var parsing cases themselves stay. Errors: no error surface beyond the smoke's own. [paraphrase]
- **R7:** The runner-timeout tests that run identical hanging-shard corpora are merged into one runner invocation whose output carries all of their assertions, so that shape pays the 12 s per-file budget once. The kill-suppressed scenario keeps its own run, because it patches the runner differently. Every existing assertion is preserved. Errors: no error surface beyond the test's own. [paraphrase]
- **R8:** The cause of the Windows-only slowdowns in `test_prime_eval.py`, `test_review_fanout.py` and `test_pr_cognitive_aid_multi_spec.py` is diagnosed from one dispatched Windows run with per-test timing, and recorded in this spec's task receipt: spawn cost, git cost, or a named fixture. Acceptance is the recorded cause; a fix is out of scope for this criterion. Errors: an inconclusive run is recorded as inconclusive with the timings captured. [paraphrase]
- **R9:** Tests that assert sentences of shipped skill prose are converted to structural assertions (heading, link, route or token present) or deleted, per G2. This covers at least `test_interview_source_tags.py` and the phrase pins in `test_work_reached_path_routes.py`, and the task names each converted test. `test_prompt_text_pinned.py` is untouched. Errors: no error surface. [paraphrase]

## Boundaries

- [user] "impl-review ... focused on overengineering and slop and yagni": implementation review judges every change against the smallest correct fix; speculative generality, unused parameters, defensive branches for impossible states, duplicated helpers, and prose that restates code are findings.
- The product CLI entry, both launchers, `flowctl_bootstrap.py`, and the product's source-authoritative startup and trust model are unchanged. The runner is test-only. fn-190 (product importable entry) stays deferred and is not touched by this wave. [paraphrase]
- No in-process `main()` harness, no shared session-scoped state across test classes, no pytest migration. [inferred]
- "do not let it go into overengineering mode" [user] - concretely: no new runner flags, no timing database or per-file duration cache, no new CI jobs beyond running the R5 check in the existing ubuntu units job, no config keys. [paraphrase]
- No fix for the Windows slowdowns in this wave (R8 is diagnosis only). [paraphrase]
- Product-side flowctl startup work (lazy imports, lazy argparse) belongs to other waves. [inferred]

## Decision Context

Importing flowctl from a tiny test runner captures the audit's measured saving (~74% per spawn) with the least change. Process isolation and exit-code semantics are preserved, so no test's meaning changes. An in-process `run_cli` harness would save more (~93%) but needs cache resets between calls and risks cross-test leakage. It was rejected for this wave. Ordering by file size needs no timing data or maintenance and was simulated to reach within ~2% of ideal longest-first. The product entry stays as fn-190's deferral left it: the test runner is not evidence against that trust-model decision, because tests run from a trusted checkout.

Review round 1 (gpt-6-astra) corrected two premises. R1 now pins `sys.argv[0]`, because argparse derives its program name from it and the output would otherwise change. R7 now merges only the identical hanging-shard runs, because the kill-suppressed scenario uses different patches.

## Strategy Alignment

Serves "Self-improving through normal work" indirectly: a cheaper gate makes every later change cheaper to verify. No flowctl surface changes, so "flowctl grows only under burden of proof" is not engaged. Cross-platform parity is preserved: the Windows leg runs the same runner and the launcher parity tests stay on the real entries.

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-256.M (TBD - populate via /flow-next:plan) |
| R2 | fn-256.M (TBD - populate via /flow-next:plan) |
| R3 | fn-256.M (TBD - populate via /flow-next:plan) |
| R4 | fn-256.M (TBD - populate via /flow-next:plan) |
| R5 | fn-256.M (TBD - populate via /flow-next:plan) |
| R6 | fn-256.M (TBD - populate via /flow-next:plan) |
| R7 | fn-256.M (TBD - populate via /flow-next:plan) |
| R8 | fn-256.M (TBD - populate via /flow-next:plan) |
| R9 | fn-256.M (TBD - populate via /flow-next:plan) |

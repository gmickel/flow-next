---
satisfies: [R17, R18, R19, R20, R21]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.11 Integration benchmark, cross-platform gate, and completion evidence

## Description
Run the final integrated verification once all tasks land. Collect the reproducible pre/post benchmark report for ordinary and specialized paths, explicitly including plugin-bin/copy help, flowctl usage, setup-mode, config, list, status, specs, prime, export, memory, cascade, and pilot. Compare deterministic operation counts and investigate every >10% regression.

Exercise Python minimum/latest, Windows locking/launcher coverage, plugin/copy modes, plugin-bin, mirrors, dogfood and Ralph copies, full Python suite, shell smokes, plugin validation, and docs build. Prepare completion-review evidence with commits, exact commands/results, benchmark tables, retained/deferred findings, and clean-worktree state. Do not bump or release.

Run a bounded live RepoPrompt Community Edition smoke on this macOS host with CE installed. Record the resolved executable/version and prove CE wins when discontinued Classic is also installed. Against one deliberate review workspace, exercise all supported `flowctl rp` wrappers (`setup-review`, prompt set/get, selection add/get, chat send, and prompt export). Invoke `setup-review --create` twice, capture window inventories before/after, and prove the second call reuses the same numeric CE window rather than cloning the workspace; tabs may differ. Use a minimal chat prompt and validate transport/session identifiers, not answer quality. Keep exports temporary and record any intentional CE tab/workspace side effects.

Complexity: 76/100.

Quick commands:
- python3 scripts/run_tests_parallel.py
- cd plugins/flow-next/scripts && bash smoke_test.sh
- ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
- claude plugin validate plugins/flow-next
- live CE smoke through `.flow/bin/flowctl rp` with pre/post `rpce-cli --raw-json -e windows` inventories
- cd ~/work/flow-next.dev && pnpm build
## Acceptance
- [ ] Final report contains reproducible pre/post medians and operation counts for help/usage/setup-mode/config/list/status/specs/prime/export/memory/cascade/pilot.
- [ ] No optimized path regresses >10% without an explicit correctness justification accepted in the evidence.
- [ ] Full parallel suite, focused platform/launcher/locking tests, shell smokes, mirror idempotency, plugin validation, and docs build pass.
- [ ] Python 3.11 and latest-stable gates pass; Windows tests prove real lock behavior.
- [ ] Canonical flowctl, plugin-bin, dogfood copy, Ralph copy, templates, and Codex mirror are synchronized with fn-121 invariants intact.
- [ ] Live CE smoke records CLI/app versions and resolver path, proves CE is selected over co-installed Classic, and exercises every supported `flowctl rp` wrapper successfully.
- [ ] Two live `rp setup-review --create` calls for the same root return the same numeric CE window; pre/post inventories prove no duplicate workspace window was created.
- [ ] CE smoke validates prompt/selection round trips, prompt export content, and a minimal chat transport/session ID; temporary files are removed and intentional CE UI state is documented.
- [ ] Worktree scope is clean apart from intended fn-122 artifacts and associated code/docs changes.
- [ ] Completion evidence lists commits/tests, retained/deferred findings, and confirms no version bump or release.
## Done summary
Completed the integrated performance, platform, documentation, and RepoPrompt CE gate for fn-122.

Same-machine wall-clock benchmark: macOS, Python 3.14.5, current checkout, 12 fresh processes per path with two warmups discarded; values are median [min-max] over 10 measured runs.

| Path | 3.1.0/reference | Final | Delta |
|---|---:|---:|---:|
| copied launcher `--help` | 0.2008s | 0.0618s [0.0600-0.0630] | -69.2% |
| plugin-bin `--help` | 0.1971s | 0.0639s [0.0630-0.0656] | -67.6% |
| direct Python `--help` | 0.1679s | 0.1679s [0.1648-0.1713] | 0.0% |
| plugin-bin `usage` | 0.2242s | 0.0602s [0.0584-0.0620] | -73.1% |
| `config get` | 0.2197s | 0.2169s [0.2151-0.2248] | -1.3% |
| `list --json` | 0.2764s | 0.2625s [0.2576-0.2700] | -5.0% |
| `status --json` | 0.2772s | 0.2625s [0.2575-0.2662] | -5.3% |
| `specs --json` | 0.3638s | 0.2636s [0.2597-0.2693] | -27.5% |
| `prime classify` | 0.5848s | 0.4748s [0.4685-0.4797] | -18.8% |
| cognitive-aid export | 0.5100s pre-.7 | 0.4629s [0.4585-0.4717] | -9.2% despite the larger final diff |
| memory list, direct-source exact reference | 0.1900s | 0.1913s [0.1873-0.1940] | +0.7% |
| setup-mode set, isolated fixture | n/a | 0.2137s [0.2112-0.2148] | current evidence |
| task reset cascade, 3-task isolated fixture | n/a | 0.2311s [0.2283-0.2352] | current evidence |
| pilot append, isolated fixture | n/a | 0.2142s [0.2126-0.2169] | current evidence |

The apparent 0.2171s memory result from the first comparison used the launcher while the 0.1900s reference was direct source. Exact direct-source replication is 0.1913s; the launcher adds the known approximately 30ms interpreter probe. No comparable optimized path regressed more than 10%.

Deterministic budgets: 404-task status/list read each eligible task exactly once and spawn zero subprocesses; specs/next/validate inventory once; Prime's 900-path Pascal fixture performs at most 1,800 lowercase calls and resolves the root once; cognitive-aid uses one unified-diff spawn and parse; memory metadata/search reads N files once each and exact full IDs read one file; pilot tick 41 reads one historical witness rather than 40 rows. Cascade uses the shared single inventory/reverse graph.

Runtime/platform evidence: full Python 3.11.14 gate passed 2,056 tests with zero failures/errors and three skips after fixing cross-minor argparse snapshot drift; final Python 3.14.5 gate passed 2,057 tests with zero failures/errors and three skips. Static root help is authenticated against source, help bytes, and the generating Python minor; other supported minors fall back to live argparse. Portable-lock concurrency/error tests, Windows launcher generation/selection contracts, plugin-bin/copy/Ralph/dogfood parity, two idempotent Codex mirror regenerations, plugin validation, CI shell smoke (67/67), and full-PATH smoke (136/136) passed. The earlier isolated Codex impl-review exit 2 did not reproduce: the final live smoke passed Codex plan and implementation reviews plus Copilot plan/re-review/implementation reviews.

Live RepoPrompt evidence: `/usr/local/bin/rpce-cli` 1.1.0 won the resolver over co-installed discontinued `/usr/local/bin/rp-cli` 2.1.33. Prompt set/get, selection add/get, prompt export, chat send, and two setup-review calls all passed. Export contained the expected prompt and README. The smoke exposed and fixed CE's bold-Markdown chat-ID parser gap; JSON then returned `untitled-chat-502101`. Both setup-review `--create` calls returned numeric window 2; before/after inventories contained only windows 1, 2, and 3 and exactly one matching flow-next workspace window, so no clone occurred. CE intentionally added two review tabs and a smoke chat to window 2. Temporary prompt/chat/export files were removed.

Root Unreleased and flow-next.dev describe the actual source-authoritative static fast paths, Python 3.11 floor, CE ladder/window reuse/chat IDs, and no version bump. Public docs commits for final-gate corrections: 65cc7d7 and e991cac; docs build completed with zero Astro diagnostics and 74 pages. No release or GitHub issue state change was made; #228 remains open for the land-time thank-you and closure.

Retained/deferred findings: no correctness or performance finding remains open in fn-122. Actual Windows-host CI remains the post-PR platform execution surface; local tests exercise the portable lock contract and generated Windows launchers. No version bump or release occurred.
## Evidence
- Commits: ea1b82c9, 3a326a59
- Tests: Python 3.11.14: python3.11 scripts/run_tests_parallel.py (2056 passed, 0 failures/errors, 3 skips), Python 3.14.5: python3 scripts/run_tests_parallel.py (2057 passed, 0 failures/errors, 3 skips), plugins/flow-next/scripts/ci_test.sh (67 passed, 0 failed), plugins/flow-next/scripts/smoke_test.sh with full PATH (136 passed, 0 failed; Codex and Copilot live reviews passed), test_hot_path_sweep test_task_inventory test_prime_performance test_export_cognitive_aid test_memory_performance test_pilot_log test_portable_locks test_startup_bootstrap (65 passed), test_rp_wrappers test_startup_bootstrap on Python 3.11 and 3.14 (30 passed on each), scripts/sync-codex.sh twice; generated mirror unchanged, claude plugin validate plugins/flow-next (passed), canonical/dogfood flowctl.py, bootstrap, and help cmp parity (passed), flow-next.dev bun x pnpm build (0 Astro diagnostics, 74 pages), live RepoPrompt CE 1.1.0 wrapper/reuse smoke (all wrappers passed; window 2 reused; chat id preserved), same-machine 12-process benchmark with two warmups discarded (10 measured runs per path; no comparable regression over 10%)
- PRs:
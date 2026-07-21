# fn-122-flowctl-hardening-and-performance-completion-sweep flowctl hardening and performance completion sweep

## Goal & Context
<!-- scope: business -->

Complete the post-fn-109–114 optimization program for `plugins/flow-next/scripts/flowctl.py`: eliminate confirmed correctness/concurrency defects, reduce remaining startup and scale costs, remove residual dead surfaces, repair active documentation and skill contracts that still describe deleted commands, and add deterministic regression gates so none of the gains regress.

The prior optimization work succeeded: on the 2026-07-21 audit checkout (`3e658c00860e7c94e5ccfccbfc02512635970e80`, 113 specs / 441 tasks), `list --json` and `status --json` fell from roughly 31–32 seconds to warm medians near 0.28 seconds (>99% reduction). The remaining general-command cost is now dominated by loading/compiling the 1.18 MB source file; specialized paths retain repeated scans and subprocesses. The audit also reproduced silent concurrent task loss, model-cache stale/lost-update behavior, Windows no-op locking, and task-scanner divergence despite a green suite.

**Rebase gate resolved (2026-07-21):** fn-121 landed in flow-next 3.1.0. This worktree was rebased from audit base `3e658c00` through the 3.1.1 patch release to implementation base `917e6521` (3.1.0 tag `a45c7631`; 3.1.1 tag `917e6521`). Task `.1` re-derived the plan below before any implementation task started.

## Post-3.1.0 Rebase Disposition

### Landed delta

- fn-121 changed 107 files overall (`+2618/-123`) but only two regions of `plugins/flow-next/scripts/flowctl.py`: 176 added lines for `cmd_usage`, `cmd_setup_mode_set`, and parser wiring. Model resolution/cache, locks, task creation, inventory, Prime, export, memory, pilot, and dead-surface code are byte-unchanged from the audit base.
- The post-release `29771254` follow-up changes only Grok bridge guidance/scaffolding, the canonical/mirrored/dogfood usage templates, Ralph documentation-truth assertions, and the Unreleased changelog. It adds no `flowctl.py` or launcher behavior. Its 28 focused scaffold/docs-truth tests pass, so it does not alter the implementation plan; task `.10` must preserve the corrected bridge syntax while repairing adjacent active contracts.
- The subsequent 3.1.1 release commit `917e6521` only advances version manifests and closes the already-landed usage-guidance patch release. It adds no `flowctl.py`, launcher, template, or test behavior and therefore does not change this plan.
- `flowctl.py` is now 30,199 lines / 1,183,997 bytes. CLI surface grew from 42 to 44 top-level commands, 22 to 23 groups, 115 to 117 leaves, and 137 to 140 command nodes; parser construction performs 566 argument registrations.
- New load-bearing surfaces: `plugins/flow-next/bin/flowctl`, `flowctl usage`, `flowctl setup-mode set`, canonical `plugins/flow-next/templates/usage.md`, plugin/copy setup modes, slim-snippet/pre-check contracts, and new mirror transforms/guards.
- Full 3.1.0 gate: 94 files, 1,957 tests, 0 failures/errors, 3 skips, 72.17 seconds.

### Refreshed warm baselines

Same worktree/machine, eight fresh processes per command with two warmups discarded:

| Path | 3.1.0 median | Disposition |
|---|---:|---|
| copied launcher `--help` | 0.2008s | startup compilation still dominates |
| plugin-bin launcher `--help` | 0.1971s | new fn-121 surface; same cost shape |
| direct Python `--help` | 0.1679s | launcher probe remains ~30ms |
| `config get "" --json` | 0.2197s | unchanged |
| `tasks --json` | 0.2704s | unchanged |
| `status --json` | 0.2772s | unchanged |
| `list --json` | 0.2764s | unchanged |
| `specs --json` | 0.3638s | repeated task-directory scans remain |
| plugin-bin `usage` | 0.2242s | new high-frequency static-guidance path; add to startup scope |
| source compile only | 0.1784s | ~64% of ordinary command latency |
| `prime classify --json` | 0.5848s | prior 2.7s sample was environment/cache-sensitive; use deterministic and synthetic budgets |

### Finding disposition

| Area | 3.1.0 disposition | Evidence / plan consequence |
|---|---|---|
| Concurrent task creation | **Confirmed** | Fresh 40-process run: 40 successes, 32 persisted, 8 acknowledged writes lost, one JSON/Markdown title mismatch. Task `.2` unchanged. |
| Windows/task/setup locking | **Confirmed** | `_flock` fallback and critical sections unchanged. Task `.2` unchanged. |
| Model cache ignores current role intent | **Confirmed** | Cache key remains `backend@cli-version`; fresh reproduction requested role pin `gpt-5.6-sol` but dispatched cached `gpt-5.5`. Task `.3` is now a definite fix, not conditional reconciliation. |
| Model-cache lost updates | **Confirmed** | Unlocked read-modify-replace functions byte-unchanged. Task `.3` unchanged. |
| Python runtime contract | **Confirmed + expanded** | Docs still advertise 3.8+, launchers check functionality only, CI runs 3.11 only. Task `.4` now includes fn-121 plugin-bin and setup/usage path resolution. |
| Startup/argparse | **Confirmed + expanded** | Source compilation unchanged; parser adds three nodes. New `usage` pays full Python startup to print static Markdown. Task `.4` adds `usage` target and must preserve logical source/template resolution if code executes from cache. |
| Task scanner divergence / repeated inventories | **Confirmed** | `status`/dependents remain `fn-*.json`; `tasks`/`list` remain all-task scans. Task `.5` unchanged. |
| Reverse dependencies | **Confirmed** | Full corpus still reparsed per visited node with `pop(0)`. Task `.5` unchanged. |
| Spawn fallback | **Confirmed** | Repo/state/version paths still omit `OSError` where flagged. Task `.2` unchanged. |
| Prime | **Confirmed, metric revised** | Pascal lowercased set still rebuilt inside loop; Git/realpath repetition remains. Use operation counts plus Pascal-heavy synthetic fixture, not a fixed repo-wall percentage. |
| Cognitive aid | **Confirmed** | Duplicate unified diff and whole-tree glossary behavior unchanged. Task `.7` unchanged. |
| Memory/pilot/frontmatter | **Confirmed** | Double reads, corpus scan, O(N²) pilot ticks, parser duplication unchanged. Task `.8` unchanged. |
| Dead surfaces | **Confirmed** | All previously identified imports/helpers/interfaces/constants remain; fn-121 additions are live and tested. Task `.9` unchanged. |
| Active docs/skills drift | **Confirmed + expanded** | Most stale commands/payload claims remain. Task `.10` must preserve fn-121 plugin-mode and `flowctl usage` truth while fixing them. |
| Test gaps | **Confirmed, suite expanded** | fn-121 added four test files and 22 tests, but concurrency/model-cache/platform/scanner/RP/completion gaps remain. Existing fn-121 contract tests become mandatory focused gates. |

## Architecture & Data Models
<!-- scope: technical -->

### 1. Post-fn-121 audit ledger and deterministic baselines

Task `.1` produced the disposition record above against audit base `3e658c00`, explicitly covering fn-121’s plugin-bin launcher, `flowctl usage`, argparse changes, embedded/generated launcher copies, usage-template move, `models.roles`, and orchestration prose. Downstream tasks use these 3.1.0 anchors and baselines.

Performance CI uses deterministic budgets (subprocess count, directory scans, JSON/content reads, parser construction where applicable), never host-dependent wall-clock thresholds. Wall-clock measurements remain required release evidence: same machine, same checkout/fixture, at least 10 warm runs after two discarded warmups, median and spread recorded.

### 2. Correctness and concurrency layer

- Add a cross-platform lock primitive with bounded acquisition, stale-owner recovery where the chosen mechanism needs it, and explicit error behavior. No Windows no-op fallback.
- Serialize per-spec task-ID allocation through paired JSON/Markdown publication. A successful create means one unique ID and matching artifacts; collision/second-write failure is explicit and leaves no half-created task.
- Catch `OSError` alongside process exit failures where repo/state/CLI-version discovery promises graceful fallback and non-sticky retries.
- Fix confirmed model-resolution caching defects: key by effective routing intent, revalidate downgrade/floor entries, and serialize cache mutation so unrelated backend entries cannot be lost. Explicit model-pin semantics remain authoritative and never silently downgrade.

### 3. Runtime and startup contract

- Minimum supported runtime becomes Python 3.11. The launcher must probe both functionality and `sys.version_info >= (3, 11)` and produce a precise “working but too old” error. The contract covers every launcher/source generated or introduced by landed fn-121, including Unix, Windows, plugin-bin, copied `.flow/bin`, Ralph copies, and embedded launcher constants.
- Prove and, if safe, ship a hash/version-validated bytecode-backed module path that preserves the inspectable pure-stdlib source distribution, falls back safely to source, and never executes stale/corrupt cache state. Revisit the earlier fn-101 pyc deferral because compilation now dominates ordinary commands. Cached execution must preserve the logical source/plugin root used by `cmd_usage` and all template/path discovery; `__file__` must not silently become an unrelated cache-root contract.
- Preserve the Windows Store-stub functionality probe. Interpreter-choice caching is permitted only with identity/version validation and automatic re-probe on failure.
- Treat `flowctl usage` as a first-class fast path: plugin mode intentionally invokes it before non-lifecycle operations/delegation, yet 3.1.0 pays ~0.224s to print static guidance. Optimize through the common startup design or a parity-tested launcher fast path across plugin/copy/Windows modes.
- Demand-driven argparse/template loading is a secondary optimization: ship only if the bytecode/startup proof leaves material cost and compatibility tests cover root/family help, `usage`, `setup-mode`, error text/exit codes, aliases, and scope argument rewriting.

### 4. Command-scoped Flow inventory

Introduce one authoritative task-file iterator and command-scoped inventory owning:

- native and tracker-key ID recognition;
- canonical/legacy layout precedence;
- artifact exclusion;
- deterministic ordering;
- spec grouping and task lookup;
- runtime-state merge/bulk loading.

Migrate `list`, `status`, `specs`, `tasks`, worst-case `next`, validation, and reverse-dependency traversal against golden output fixtures. Reverse dependencies build one adjacency map and traverse via `collections.deque`; no per-node full-corpus reparsing. Either make `StateStore` provide a meaningful bulk snapshot/deletion boundary or collapse the single-implementation seam without changing persistence behavior.

### 5. Specialized hot paths

- **Prime:** precompute the case-insensitive tracked-path set, cache containment roots/realpaths, and batch or safely parallelize independent Git probes. Preserve bounded reads, redaction, and classification output.
- **Cognitive aid:** generate/parse the unified diff once; derive glossary candidates from changed paths; avoid complete worktree/base-tree scans and per-unchanged-glossary `git show` calls.
- **Memory:** parse each entry from one buffer, provide metadata-only iteration, resolve validated full IDs directly, and select the optional YAML parser once per process.
- **Pilot log:** maintain next-tick state under the existing per-ID lock; scan historical rows only to recover absent/corrupt counter state.
- **Frontmatter:** centralize envelope parsing while preserving schema-specific coercion and the distinct absent/malformed contracts for strategy, memory, and prospect.

### 6. Dead surface and contract repair

Remove only post-rebase-proven dead surfaces: unused imports, the unreachable strategy validator and exclusive constants, unused StateStore enumeration, `save_task_definition`, `require_keys`, `_memory_yaml_available`, and inert `TRACKER_TIEBREAKS`. Rewrite the strategy smoke around the real direct-edit/read contract, then remove the test-only `render_strategy_file`. Keep documented/tested compatibility seams.

Repair active documentation and skills after a fresh post-fn-121 grep, including the known stale references to epic aliases, `migrate-rename`, `config toggle`, Ralph `unblock`/`update`, global `--version`/`setup`, unnamespaced review commands, bare strategy `flowctl`, nonexistent `strategy list`, removed export `--section`/`review_receipts`, and deleted RP `pick-window`/`builder`. Historical specs/tasks/changelog/eval fixtures remain historical evidence and are excluded from active-reference gates.

### 7. RepoPrompt Community Edition compatibility ladder

RepoPrompt Community Edition is the primary supported RP backend; discontinued Classic support is compatibility-only. Use one deterministic executable ladder: `rpce-cli` on PATH → current CE user link `~/RepoPrompt/repoprompt_ce_cli` → legacy CE application-support link `~/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli` → `rp-cli` as the final Classic fallback. Candidate absence, a broken link, or a non-executable file may advance the ladder. Once a CE candidate is selected, its connection, timeout, protocol, or command failure is authoritative and must not silently downgrade to Classic.

Treat CE 1.1.0's live response shapes as canonical: selected windows may be under `binding.window_id`, while repository roots are under `windows[].tabs[].repo_paths`. Preserve legacy `result`/`data` wrappers, top-level root keys, and Classic execution as explicit regression compatibility. Task `.9` owns deterministic discovery/parser/setup-review tests; task `.11` owns a bounded live CE smoke across every supported `flowctl rp` wrapper and proves repeated `setup-review --create` reuses one window.

## API Contracts
<!-- scope: technical -->

- Existing supported CLI commands, JSON shapes, text ordering, exit codes, compatibility aliases, and atomic-file semantics remain unchanged unless this spec explicitly corrects a documented defect.
- `task create` success guarantees a unique task ID plus mutually matching JSON and Markdown. Concurrent creators either all succeed uniquely or receive explicit failures; no acknowledged write may disappear.
- Locking provides actual inter-process exclusion on macOS, Linux, and Windows. Timeout/stale-owner behavior is deterministic and tested.
- Explicit model selections remain explicit: no probing/cache-driven downgrade. Unconfigured/role-map resolution behavior follows the post-fn-121 disposition record and is tested as an integrated precedence chain.
- Supported Python is `>=3.11`; older working interpreters are rejected before loading `flowctl.py` with actionable remediation.
- Cached startup artifacts are optional accelerators, never sources of truth. Missing, stale, unwritable, or corrupt cache state falls back to source execution without changing command output or plugin/template path resolution.
- Task inventory consumers see the same eligible task universe, including tracker-key tasks; caller-specific filtering is layered above one scanner.
- RP backend discovery prefers RepoPrompt CE through the pinned ladder (`rpce-cli` → current CE user link → legacy CE link → Classic `rp-cli`). Discovery-only failures advance; operational failures from a selected CE executable never downgrade to Classic.
- CE/current `binding.window_id` and `windows[].tabs[].repo_paths` payloads are authoritative. Legacy wrappers/root keys remain accepted without changing the external `flowctl rp` command surface.
- No new external Python dependency. PyYAML remains optional; pure-stdlib behavior stays complete.

## Edge Cases & Constraints
<!-- scope: technical -->

- fn-121 / flow-next 3.1.0 is now a formal completed dependency. Preserve its plugin-mode invariants, new launcher, `usage`/`setup-mode` commands, canonical usage-template location, slim snippet, and mirror transforms/guards.
- Preserve fn-77’s Windows Store-alias defense and fn-109’s cwd-keyed, success-only repo/state caches. Failed probes remain retryable.
- Preserve fn-52 tracker-key behavior, canonical/legacy layout rules, output sorting, malformed-file tolerance, and runtime-state precedence while centralizing scans.
- Preserve fn-76/fn-115 explicit model precedence and fail-soft intent unless the post-fn-121 audit proves the landed contract changed.
- Preserve cognitive-aid rename/deletion semantics, same-file re-add suppression, protected-path handling, R-ID coverage, and stable payload order.
- RepoPrompt CE and discontinued Classic may coexist. Every capability probe, generated mirror, and smoke must select CE first; Classic remains a last-resort compatibility fallback, never an operational retry target.
- Live CE verification is macOS-local evidence, not a CI requirement. It uses deliberate bounded state, temporary exports, pre/post window inventories, and records any retained CE tabs/workspaces.
- Cache/lock files stay gitignored and recoverable. Never use a broad destructive cleanup path.
- Do not convert flowctl into an agentic judgment engine; all changes remain deterministic plumbing.
- Canonical skill edits require `scripts/sync-codex.sh` twice and committed mirror parity. User-facing behavior/docs changes propagate to `~/work/flow-next.dev` in the same workstream.
- Version bumps remain batched: stage `## Unreleased` entries; do not run `scripts/bump.sh` or alter version manifests.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The checked-in 3.1.0 disposition ledger refreshes every audit finding and baseline against the landed tree, names changed/superseded assumptions, and records current evidence for model resolution/cache, launcher/runtime, argparse, usage-template, mirror, and active-doc surfaces.
- **R2:** A real 20–40-process concurrent `task create` test produces unique IDs and matching JSON/Markdown for every acknowledged success; injected second-write failure/collision leaves no half-created or overwritten task.
- **R3:** Task/runtime/setup/model-cache critical sections use real cross-process locking on POSIX and Windows; race tests prove exactly-one-winner or lossless merge semantics as appropriate; no platform degrades to a no-op lock.
- **R4:** Confirmed stale-role/floor behavior is fixed and tested across role-map mutation; cache writes/invalidation preserve concurrent unrelated entries; explicit pins bypass downgrade behavior.
- **R5:** Runtime contract is Python 3.11+ across README, platform/install/update docs, launchers, generated/embedded copies, and CI. Probes reject 3.10 with actionable output and accept 3.11/latest; full gate runs on 3.11 and latest stable, with lightweight intermediate-version smoke coverage.
- **R6:** Repo/state/version subprocess discovery catches `FileNotFoundError`, `PermissionError`, and equivalent `OSError` paths without sticky failure; later successful probes work.
- **R7:** One task scanner/inventory supplies all backlog consumers. `status`, `tasks`, `list`, dependency traversal, and validation agree on tracker-key/native tasks and artifact exclusions; golden text/JSON ordering remains unchanged.
- **R8:** Reverse-dependency traversal loads each eligible task at most once plus constant overhead and handles chain, diamond, cycle, malformed-file, cross-spec, and tracker-key fixtures. `specs`, worst-case `next`, and `validate --all` perform one task-directory inventory scan per command.
- **R9:** A safe bytecode/module/common startup path reduces 3.1.0 warm median `--help`, `usage`, and simple-command latency by at least 35% and `list`/`status` by at least 20% versus the task-.1 baseline, without stale-cache execution, path-resolution drift, or output drift. If the proof cannot meet safety and benefit together, task `.4` records the evidence and ships the strongest safe launcher/runtime improvements; no risky cache is accepted merely to hit the target.
- **R10:** Any shipped interpreter, cached-module, launcher-usage, or argparse fast path preserves root/subcommand help, `usage` canonical/fallback resolution, `setup-mode` invariants, error text and exit codes, aliases, `scope resolve` rewriting, Windows launcher behavior, plugin/copy mode, and source fallback. Deterministic tests cover selection and invalidation; no CI wall-clock assertion.
- **R11:** Prime removes the Pascal O(P×N) lowercasing defect, avoids repeated root realpaths, reduces independent Git-process work, and preserves classification/redaction. Deterministic operation counts and a Pascal-heavy synthetic fixture prove the asymptotic improvement; repo-wall measurements are evidence only because the unchanged 3.1.0 code varied heavily with filesystem/cache state.
- **R12:** Cognitive-aid export invokes the unified diff once, analyzes changed glossary candidates only, and produces byte-equivalent payloads across rename/delete/re-add/protected-path fixtures with deterministic subprocess budgets.
- **R13:** Memory list/read/search use one content read per entry plus constant target overhead; fully-qualified IDs resolve directly with containment validation. Pilot steady-state append is O(1) historical-row reads with recovery tests. Shared frontmatter parsing preserves optional-PyYAML and fallback coercion/sentinel behavior.
- **R14:** Post-rebase reachability scan removes all confirmed dead imports/helpers/test-only production code while preserving explicit compatibility surfaces. Every registered CLI leaf remains handler-bound and active-callsite proof is retained for non-obvious workflow imports.
- **R15:** Active repo docs, agent docs, skills, smoke labels, generated Codex mirror, and flow-next.dev no longer instruct any deleted/nonexistent command or payload field. A scoped executable-snippet/reference gate excludes historical records and frozen eval fixtures.
- **R16:** Coverage gaps are closed for completion-review state mutation, every supported RP wrapper, CE/current plus legacy response schemas, 400+ task `status` budgets, concurrent create/locking/model cache, Python-minimum launch, tracker-key scanner parity, and the live plan-workflow invocation manifest.
- **R17:** Canonical/mirror/generated copies stay synchronized: `scripts/sync-codex.sh` twice is idempotent; plugin-bin/copy/Ralph launcher, dogfood/template parity, and `claude plugin validate` pass; fn-121 plugin-mode invariants remain intact.
- **R18:** Final evidence reports pre/post medians and deterministic operation counts for help/usage/setup-mode/config/list/status/specs/prime/export/memory/cascade/pilot paths. No optimized path regresses more than 10% versus the 3.1.0 baseline without an explicit correctness justification.
- **R19:** Focused suites pass per task; final gate passes `python3 scripts/run_tests_parallel.py`, plugin smoke tests, launcher/platform tests, and relevant shell smokes on a clean worktree. No existing tests are removed merely to obtain green.
- **R20:** Root and docs-site `## Unreleased` entries describe behavior/runtime changes; public docs build passes; no version bump or release occurs in this spec.
- **R21:** RepoPrompt integration is CE-first through the explicit executable ladder, never downgrades after a selected CE operational failure, parses live CE `binding`/tab-root schemas without losing legacy compatibility, and passes deterministic discovery/setup-review tests. A final live CE 1.1+ smoke selects CE over a co-installed Classic app, exercises every supported `flowctl rp` wrapper, validates prompt/selection/export/chat round trips, and proves two `setup-review --create` calls for one root reuse the same numeric window without cloning the workspace.

## Boundaries
<!-- scope: business -->

- fn-121’s shipped plugin/copy-mode behavior is fixed input, not redesign scope.
- No broad multi-file rewrite solely to reduce `flowctl.py` line count.
- No removal of compatibility surfaces based only on static reachability; documented/tested workflow imports remain supported.
- No new command, skill, agent, external dependency, database, daemon, or long-lived indexing service.
- No change to deterministic-vs-agentic architecture or licensed subprocess-LLM carve-outs.
- No model-routing redesign beyond the defects confirmed in the 3.1.0 disposition ledger.
- No absolute wall-clock thresholds in CI.
- No release/version bump; no destructive cleanup of user `.flow` state.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

The high-level optimization is already successful, but the remaining defects sit on trust boundaries: concurrent agents can lose acknowledged tasks, Windows locking does not lock, cached model choices can ignore current intent, and active docs can send users to commands that no longer exist. Finishing this work now protects the performance gains while the audit evidence is fresh and before more features compound duplicated scanners and launch paths.

Python 3.8 compatibility is intentionally dropped. It reached upstream EOL in 2024; 3.9 in 2025; 3.10 reaches EOL in October 2026. Python 3.11 is the balanced floor: supported through October 2027, default on Debian 12, available on Ubuntu 22.04, and less exclusionary than 3.12.

### Implementation Tradeoffs
<!-- scope: technical -->

Correctness precedes speed. The plan first freezes post-fn-121 truth and adds characterization around concurrency, platform, and compatibility seams. Startup work follows an early proof because direct-script source compilation is now the largest universal cost, but a stale or opaque bytecode cache would be worse than the latency it saves. Shared inventory is preferred over isolated micro-caches because it simultaneously fixes task-universe divergence and removes repeated scans. Specialized optimizations remain separate tasks so regressions are attributable and reviewable.

Rejected: a monolithic refactor of the 30k-line file; deleting every statically unreferenced symbol; dropping the Windows Store probe; keeping Python 3.10 for only three months of upstream runway; forcing lazy argparse before proving bytecode startup; wall-clock CI gates; and treating fn-121’s new static `usage` path as free.

## Strategy Alignment

- **Fast deterministic plumbing:** ordinary lifecycle commands remain sub-second and scale linearly.
- **Cross-platform parity:** Windows gets real locking and an explicit runtime contract rather than silent degradation.
- **Spec-driven trust:** acknowledged task writes become durable; tests and active documentation describe the actual contract.
- **Maintainable plugin distribution:** zero-dependency/source-first remains intact while startup acceleration is safely cached and reversible.

## Quick commands

```bash
# Focused core suites; tasks refine these lists after the fn-121 rebase audit.
cd plugins/flow-next/tests && python3 -m unittest \
  test_hot_path_memoization test_hot_path_sweep test_task_create_files \
  test_model_resolution test_export_traceability test_memory_read \
  test_config_snapshot -q

# Mirror / launcher parity where canonical skills or launchers change.
./scripts/sync-codex.sh && ./scripts/sync-codex.sh

# Full gate once at completion review.
python3 scripts/run_tests_parallel.py && \
  (cd plugins/flow-next/scripts && bash smoke_test.sh)
```

## Plan (11 tasks)

1. **`.1` — Post-fn-121 rebase audit and characterization ledger** — complexity **45/100**, no task deps; completed against 3.1.0 in the disposition section above. Satisfies R1 and establishes R18 baseline.
2. **`.2` — Transactional task creation, portable locks, spawn-fallback hardening** — complexity **82/100**, depends `.1`. Implement per-spec allocation/publication locking, matching paired writes/rollback, real Windows locking for task/setup critical sections, and `OSError` fallback semantics with subprocess race tests. Satisfies R2, R3, R6.
3. **`.3` — Confirmed model-resolution/cache fixes** — complexity **70/100**, depends `.1`. Fix stale role-intent/floor and lost-update defects unchanged in 3.1.0; add role-mutation, expiry/reprobe, concurrent put/invalidate, and explicit-pin regression tests. Satisfies R4.
4. **`.4` — Python 3.11 runtime contract and startup acceleration proof** — complexity **86/100**, depends `.1`. Update plugin-bin/copy/Ralph/Windows/generated launchers and CI/docs; prove hash-validated cached-module execution and interpreter selection; preserve `cmd_usage` logical template resolution; optimize the 0.224s `usage` path; evaluate lazy argparse/template loading only if still material. Satisfies R5, R9, R10.
5. **`.5` — Unified task inventory, scanner parity, reverse dependencies, bulk state** — complexity **84/100**, depends `.1`. Centralize task discovery/state projection, migrate backlog consumers, build one reverse graph, and complete/collapse StateStore around bulk behavior with golden output and operation-count tests. Satisfies R7, R8 and the StateStore portion of R13.
6. **`.6` — Prime classifier performance pass** — complexity **62/100**, depends `.1`. Remove quadratic lowercase construction, cache containment roots, reduce Git probes/read repetition, preserve redaction/classification, and prove gains with deterministic counts plus a Pascal-heavy synthetic fixture. Satisfies R11.
7. **`.7` — Cognitive-aid diff and glossary performance pass** — complexity **64/100**, depends `.1`. Share one unified diff/event stream, derive changed glossary paths, batch base reads, and lock semantic parity/subprocess counts. Satisfies R12.
8. **`.8` — Memory, pilot-log, and frontmatter performance pass** — complexity **72/100**, depends `.1`. Single-buffer memory parsing/direct IDs, metadata-only scans, O(1) pilot tick state/recovery, optional YAML selection cache, and schema-specific coercion over one envelope parser. Satisfies remaining R13.
9. **`.9` — Dead-surface removal and focused coverage closure** — complexity **74/100**, depends `.2,.3,.4,.5,.6,.7,.8`. Re-run reachability after refactors, remove confirmed dead/test-only surfaces, close completion-review/status/live-manifest gaps, implement the CE-first executable ladder and issue-#228 schema/window-reuse fix, update active capability probes, and add deterministic coverage for every RP wrapper plus legacy compatibility. Satisfies R14, R16, R21.
10. **`.10` — Active docs, skill contracts, mirror, and docs-site repair** — complexity **58/100**, depends `.9`. Repair all active deleted-command/payload references while preserving 3.1.0 plugin-mode and `flowctl usage` truth; add scoped drift gate, regenerate mirror twice, update public docs and Unreleased entries, build docs site. Satisfies R15, R17, R20.
11. **`.11` — Integration benchmark, cross-platform gate, and completion evidence** — complexity **76/100**, depends `.10`. Run the complete matrix/smokes, collect counts/timings including `usage` and `setup-mode`, investigate any >10% regression, verify plugin-bin/copy/Ralph/mirror state, then run the bounded live CE smoke across every `flowctl rp` wrapper and prove repeated setup reuses one window. Prepare completion-review evidence. Satisfies R18, R19, R21 and final verification for all requirements.

### Requirement coverage

| Requirement | Task(s) |
|---|---|
| R1 post-fn-121 disposition gate | .1 |
| R2 transactional concurrent create | .2 |
| R3 portable locking | .2 |
| R4 model cache/precedence | .3 |
| R5 Python 3.11 | .4 |
| R6 spawn fallback | .2 |
| R7 unified inventory/parity | .5 |
| R8 linear scan/dependency budgets | .5 |
| R9 startup improvement | .4 |
| R10 launcher/parser compatibility | .4 |
| R11 prime | .6 |
| R12 cognitive aid | .7 |
| R13 memory/pilot/frontmatter/state | .5, .8 |
| R14 dead surfaces | .9 |
| R15 active contract repair | .10 |
| R16 coverage gaps | .2–.5, .9 |
| R17 generated/mirror parity | .4, .10 |
| R18 benchmark evidence | .1, .4–.8, .11 |
| R19 complete gates | .11 |
| R20 docs/changelog, no bump | .10, .11 |
| R21 RepoPrompt CE ladder, schemas, and live smoke | .9, .11 |

---
satisfies: [R14, R16, R19, R21]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.9 Dead-surface removal and focused coverage closure

## Description
Re-run AST/repository reachability after all functional refactors. Remove only confirmed dead imports/helpers/constants/interfaces. Rewrite strategy smoke around the actual direct-edit/read contract before removing the test-only renderer. Preserve workflow-imported prospect helpers and explicit compatibility seams.

Close remaining focused gaps: completion-review persisted state, five live RP wrappers, status scale budgets, live plan-workflow invocation manifest, CLI leaf/handler inventory, and any rebase-led gaps assigned by task .1.

Fold in GitHub #228, the confirmed RepoPrompt window-reuse regression, with RepoPrompt Community Edition as the supported primary target. Live CE 1.1.0 (`rpce-cli`) confirms `bind_context` identifies the selected window at `binding.window_id`, while `windows` exposes repository roots under `windows[].tabs[].repo_paths`. The current parsers recognize only `result`/`data` wrappers and legacy top-level root keys, so `rp setup-review --create` can miss an existing worktree and clone it into a new window. Extend both parsers without dropping legacy shapes, and test the complete setup-review decision path so an existing matching window never reaches workspace switch/create.

Implement one explicit executable-selection ladder: (1) `rpce-cli` on PATH, (2) current CE user link `~/RepoPrompt/repoprompt_ce_cli`, (3) legacy CE link `~/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli`, then (4) discontinued `rp-cli` only as a final Classic compatibility fallback. Fall through only when a candidate is absent, broken, or non-executable. Once CE is selected, connection, timeout, protocol, or command failure is authoritative and must never silently retry against Classic. Update active setup/Ralph/review capability probes in the same change; task .10 aligns longer-form platform/troubleshooting prose and Unreleased notes.

Complexity: 74/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_cursor_review_commands test_backend_spec test_hot_path_memoization test_skill_prose_diet test_rp_wrappers -q
- relevant strategy/RP shell smokes
## Acceptance
- [ ] Post-refactor AST plus active-source search proves every removed symbol has no supported caller.
- [ ] Unused imports, unreachable strategy validator/constants, unused StateStore enumeration, save_task_definition, require_keys, _memory_yaml_available, inert TRACKER_TIEBREAKS, and test-only renderer are removed when still dead.
- [ ] Strategy smoke exercises the real production contract before renderer removal.
- [ ] All 115+ post-fn-121 CLI leaves remain handler-bound; non-obvious workflow imports have active-callsite evidence.
- [ ] Completion-review state, five RP wrappers, status scale, and live invocation-manifest gaps have deterministic tests.
- [ ] RepoPrompt Community Edition is the primary supported RP target. Flowctl resolves `rpce-cli`, the current `~/RepoPrompt/repoprompt_ce_cli` user link, and the legacy CE application-support link before any final `rp-cli` Classic compatibility fallback; a machine with both apps demonstrably selects CE.
- [ ] Ladder fallthrough occurs only for absent, broken, or non-executable candidates. A selected CE candidate's connection/runtime/protocol failure is returned unchanged and never triggers Classic execution.
- [ ] Missing-CLI diagnostics name RepoPrompt CE and `rpce-cli`; discovery tests mock PATH/home, cover executable/non-executable/broken-link cases, and require no installed app.
- [ ] GitHub #228 is fixed: `extract_response_window_id` recognizes `binding.window_id` through the supported wrapper recursion while preserving legacy `result`/`data` shapes.
- [ ] `extract_root_paths` combines and deterministically deduplicates legacy top-level roots with modern `tabs[].repo_paths` and `tabs[].repoPaths`, tolerating malformed/partial tab entries.
- [ ] Deterministic `rp setup-review --create` fixtures cover both modern reuse routes—successful `bind_context` and `windows[].tabs[]` root matching—and prove neither route calls `manage_workspaces` switch/create or `workspace create`; the builder receives the reused numeric window.
- [ ] CE/current response fixtures are authoritative; legacy Classic response fixtures remain green as compatibility coverage. Parser-only and discovery tests require no live RepoPrompt app.
- [ ] Compatibility false positives remain present and pinned.
- [ ] Focused suites pass; no test is deleted merely to obtain green.
## Done summary
Completed the dead-surface, focused-coverage, and RepoPrompt CE compatibility pass.

- Removed confirmed dead imports, strategy renderer/validator-only constants and functions, task-definition writer, key validator, YAML availability shim, and inert tracker tiebreaks. Retained StateStore bulk loading and workflow-imported prospect helpers with active-callsite proofs.
- Rewrote strategy smoke coverage around the real direct-edit/read contract.
- Pinned the exact 117 CLI leaf paths and callable handlers, the live plan-workflow command manifest, completion-review persisted state, and 404-task status/list read budgets.
- Added the CE-first executable ladder: PATH `rpce-cli`, current CE user link, legacy CE application-support link, then Classic `rp-cli`. Absent/broken/non-executable candidates fall through; selected CE failures never downgrade.
- Added CE schema support for `binding.window_id` and `windows[].tabs[].repo_paths`/`repoPaths`, deterministic root deduplication, `create_if_missing` first-run binding, and strict bind protocol validation.
- Covered both modern reuse routes and proved they never reach workspace switch/create. Classic missing-tool behavior remains the sole capability fallback; legacy response fixtures stay green.
- Updated active setup, review, Ralph, and RP smoke probes to the same CE-first ladder; regenerated the Codex mirror twice idempotently.

Live CE 1.1.0 evidence: first empty-repo setup created window 3 and the immediate repeat reused window 3; two setup calls for this worktree both reused window 2. Prompt get/set, selection get/add, prompt export, and chat-send all succeeded; chat returned `CE_SMOKE_OK`. Classic 2.1.33 remained installed but was never selected.
## Evidence
- Commits: a999399f, 0e9728ff, c029d0eb, 7317a713
- Tests: 246 focused RP/surface/review/backend/hot-path/inventory/startup tests passed, plugins/flow-next/scripts/ci_test.sh: 67 passed, 0 failed, plugins/flow-next/scripts/strategy_smoke_test.sh: 62 passed, 0 failed, scripts/sync-codex.sh twice: idempotent validation passed, RepoPrompt CE 1.1.0 live: first-run create, repeated same-window reuse, prompt-get, prompt-set, select-get, select-add, prompt-export, chat-send, canonical/dogfood flowctl.py cmp parity and bootstrap hash tests, Codex implementation review round 4: SHIP
- PRs:
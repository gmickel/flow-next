---
satisfies: [R14, R16, R19]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.9 Dead-surface removal and focused coverage closure

## Description
Re-run AST/repository reachability after all functional refactors. Remove only confirmed dead imports/helpers/constants/interfaces. Rewrite strategy smoke around the actual direct-edit/read contract before removing the test-only renderer. Preserve workflow-imported prospect helpers and explicit compatibility seams.

Close remaining focused gaps: completion-review persisted state, five live RP wrappers, status scale budgets, live plan-workflow invocation manifest, CLI leaf/handler inventory, and any rebase-led gaps assigned by task .1.

Fold in GitHub #228, the confirmed RepoPrompt 2.1.33 window-reuse regression. Modern `bind_context` identifies the selected window at `binding.window_id`, while modern `windows` inventory exposes repository roots under `windows[].tabs[].repo_paths`. The current parsers recognize only `result`/`data` wrappers and legacy top-level root keys, so `rp setup-review --create` can miss an existing worktree and clone it into a new window. Extend both parsers without dropping legacy shapes, and test the complete setup-review decision path so an existing matching window never reaches workspace switch/create.

Complexity: 70/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_cursor_review_commands test_backend_spec test_hot_path_memoization test_skill_prose_diet test_rp_wrappers -q
- relevant strategy/RP shell smokes
## Acceptance
- [ ] Post-refactor AST plus active-source search proves every removed symbol has no supported caller.
- [ ] Unused imports, unreachable strategy validator/constants, unused StateStore enumeration, save_task_definition, require_keys, _memory_yaml_available, inert TRACKER_TIEBREAKS, and test-only renderer are removed when still dead.
- [ ] Strategy smoke exercises the real production contract before renderer removal.
- [ ] All 115+ post-fn-121 CLI leaves remain handler-bound; non-obvious workflow imports have active-callsite evidence.
- [ ] Completion-review state, five RP wrappers, status scale, and live invocation-manifest gaps have deterministic tests.
- [ ] GitHub #228 is fixed: `extract_response_window_id` recognizes `binding.window_id` through the supported wrapper recursion while preserving legacy `result`/`data` shapes.
- [ ] `extract_root_paths` combines and deterministically deduplicates legacy top-level roots with modern `tabs[].repo_paths` and `tabs[].repoPaths`, tolerating malformed/partial tab entries.
- [ ] Deterministic `rp setup-review --create` fixtures cover both modern reuse routes—successful `bind_context` and `windows[].tabs[]` root matching—and prove neither route calls `manage_workspaces` switch/create or `workspace create`; the builder receives the reused numeric window.
- [ ] Legacy RepoPrompt response fixtures remain green, and parser-only tests require no live RepoPrompt app.
- [ ] Compatibility false positives remain present and pinned.
- [ ] Focused suites pass; no test is deleted merely to obtain green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R14, R16, R19]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.9 Dead-surface removal and focused coverage closure

## Description
Re-run AST/repository reachability after all functional refactors. Remove only confirmed dead imports/helpers/constants/interfaces. Rewrite strategy smoke around the actual direct-edit/read contract before removing the test-only renderer. Preserve workflow-imported prospect helpers and explicit compatibility seams.

Close remaining focused gaps: completion-review persisted state, five live RP wrappers, status scale budgets, live plan-workflow invocation manifest, CLI leaf/handler inventory, and any rebase-led gaps assigned by task .1.

Complexity: 66/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_cursor_review_commands test_backend_spec test_hot_path_memoization test_skill_prose_diet -q
- relevant strategy/RP shell smokes
## Acceptance
- [ ] Post-refactor AST plus active-source search proves every removed symbol has no supported caller.
- [ ] Unused imports, unreachable strategy validator/constants, unused StateStore enumeration, save_task_definition, require_keys, _memory_yaml_available, inert TRACKER_TIEBREAKS, and test-only renderer are removed when still dead.
- [ ] Strategy smoke exercises the real production contract before renderer removal.
- [ ] All 115+ post-fn-121 CLI leaves remain handler-bound; non-obvious workflow imports have active-callsite evidence.
- [ ] Completion-review state, five RP wrappers, status scale, and live invocation-manifest gaps have deterministic tests.
- [ ] Compatibility false positives remain present and pinned.
- [ ] Focused suites pass; no test is deleted merely to obtain green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

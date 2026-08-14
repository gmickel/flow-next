---
satisfies: [R6, R8]
---
# flow-98-remove-packaged-codex-delegation.4 Retire or repoint the delegation tests, and settle the ralph-guard question

## Description
Delete the tests that exist only for the packaged path, repoint the ones that assert something still true, and record the explicit decision on what the Ralph guard keeps once bridges are prose-routed.

**Size:** M
**Files:** `plugins/flow-next/tests/test_codex_delegation_classify.py`, `test_codex_delegation_gates.py`, `test_work_delegate_config.py`, `test_ralph_guard_codex_delegation.py` (delete or repoint), plus delegation assertions inside `test_model_resolution.py`, `test_hot_path_sweep.py`, `test_work_reached_path_routes.py`, `test_model_pin_ceremony_prose.py`; `plugins/flow-next/scripts/hooks/ralph-guard.py` (only if the decision says so)
**Touches:** [plugins/flow-next/tests/**, plugins/flow-next/scripts/hooks/ralph-guard.py]

### Approach
- Classify each of the four dedicated files first: purely-delegation (delete) versus asserting a surviving invariant under a delegation-shaped name (repoint, keep the substance).
- Then sweep the shared files for delegation assertions. A test that gets EASIER after this change is a regression, not a cleanup - if an assertion has to weaken, say so explicitly in the summary and justify it.
- **The ralph-guard question is already answered in the spec: revert, do not widen.** The guard's delegation amendment (the canonical-invocation recognizer, the allowed sandbox-flag list, the accepted scratch-path shape) exists to bound one machine-generated command shape and reverts with it. Restore the guard to its pre-amendment behavior; add nothing for prose-routed bridges. Ralph is deprecated and predates the packaged path, so it simply returns to what it did before.
- Record the revert in the task summary and write one memory decision entry noting the accepted trade: for prose-routed bridges the safety rule is prose-only, which is weaker than a hook and deliberate.

### Investigation targets
**Required** (read before coding):
- the four dedicated delegation test files - classify each
- `plugins/flow-next/scripts/hooks/ralph-guard.py` - what the guard actually enforces and how it detects a delegated child

### Key context
- Deleting a test because the feature is gone is correct; weakening a test so a diff passes is the thing this project treats as a defect.

### Acceptance
- [ ] Each of the four dedicated files deleted or repointed with the classification recorded
- [ ] Shared files carry no delegation assertions; no surviving assertion weakened without an explicit justification
- [ ] The ralph-guard decision is recorded with its reasoning (keep-and-widen, or drop-and-state-the-weakening), and a memory decision entry written
- [ ] Full suite green

## Acceptance
- [ ] TBD

## Done summary
Retired the packaged-delegation test surface (three files deleted outright, one deleted after repointing its surviving invariants) and reverted the ralph-guard delegation amendment per the spec's R8 decision, with the accepted prose-only trade recorded in memory.

### Classification of the four dedicated files

- `test_codex_delegation_classify.py` - purely delegation (classify-result / rollback-plan helpers + the deleted reference's prose contract) -> DELETED. Its `fixtures/mock-codex/` fixture had no other consumer -> deleted with it. The `flowctl codex classify-result` / `rollback-plan` verbs stay alive-but-untested here by design; task .5 owns their removal.
- `test_codex_delegation_gates.py` - purely delegation (pre-flight platform/recursion gates extracted from the deleted `references/codex-delegation.md`) -> DELETED.
- `test_work_delegate_config.py` - purely delegation (the six `work.delegate*` defaults + the activation-precedence resolver) -> DELETED. Every surviving invariant it carried is already pinned by `test_removed_delegate_config_advisory.py` (no `work` namespace in defaults, removed keys read as unset, `delegate` is not a model role); its `work.*` vs `tracker.perEvent.work.*` coexistence assertions are moot now that no top-level `work` block exists.
- `test_ralph_guard_codex_delegation.py` - MIXED -> DELETED after REPOINTING. Its delegation-shape assertions went with the amendment; the pre-amendment guard invariants it also happened to cover moved verbatim in substance to `test_ralph_guard.py::CodexSectionGuardTestCase`: direct `codex exec` blocked, direct `codex review` blocked, `--last` blocked through a `flowctl codex` wrapper, copilot blocked, wrapper allowed, non-codex allowed. Its version-constant test was already duplicated by `test_ralph_guard.py::DeadWeightTestCase` (no repoint needed).

### Ralph-guard: reverted, not widened (R8)

Removed from `plugins/flow-next/scripts/hooks/ralph-guard.py`: `is_canonical_codex_delegation`, `_scratch_dir_of`, `_SCRATCH_BASENAMES`, `_DELEGATE_YOLO_FLAG` + the `-s workspace-write` sandbox allowlist, and the codex-section early-pass (plus its block-message addendum and the `not is_delegation` qualifier on the `--last` screen). The section is byte-equivalent in behavior to its pre-fn-55 form. Nothing was added for prose-routed bridges: the guard's allowlist existed to bound one machine-generated command shape, that generator is gone, and Ralph is deprecated. The accepted consequence - "the bridge child writes code, the host keeps git and judgment" is prose-only (`.flow/usage.md`, R9b), weaker than a hook - is stated in the spec and in the memory entry `knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14`.

### Strengthened, not weakened

Two regrowth guards added that did not exist before: the old canonical `FLOW_DELEGATE_CODEX=1 codex exec …` shape now asserts BLOCKED end-to-end through the hook, and the guard module is asserted to carry no `is_canonical_codex_delegation` / `_scratch_dir_of` / `FLOW_DELEGATE_CODEX` at all. No surviving assertion was weakened.

### Shared-file sweep

- `test_work_reached_path_routes.py` - already repointed by task .2 (delegation-route regrowth guard); untouched.
- `test_hot_path_sweep.py` - its "delegate" hits are mock-delegate plumbing, not delegation; untouched.
- `test_model_pin_ceremony_prose.py` - dropped `delegate` from the pinned role list (task .1 removed it from `flowctl.MODEL_ROLES`, so the pin was asserting a role flowctl now rejects).
- `test_land_config.py`, `test_drive_headless_determination.py` - docstrings pointed at the deleted test files; repointed (comment-only).

### Handover to task .5 (out of this task's write scope)

- `skills/flow-next-setup/workflow.md` still offers `Scaffold + enable codex delegation`, still writes `work.delegateConsent`, and still lists `delegate` in the `models.roles.<...>` key line - all removed keys/roles. `test_model_routing_scaffold.py` pins that prose (lines ~370-376) and `test_model_pin_ceremony_prose.py` will want a positive "no delegate role" regrowth assertion once the prose moves. Both tests must change WITH that prose, not before it - removing the assertions first would have weakened them.
- The `flowctl codex classify-result` / `rollback-plan` subcommands now have zero tests and zero callers (as the conductor directed).
- `plugins/flow-next/docs/ralph.md` and `agent_docs/local-dev.md` still mention `is_canonical_codex_delegation` / `FLOW_DELEGATE_CODEX`; the codex mirror carries the whole deleted reference.

### Gate

Full suite `suite_rc=1`, but the failure set is IDENTICAL to the pre-edit baseline captured in Phase 1 (dogfood copy / tracker manifest / codex mirror propagation - `test_tracker_distribution`, `test_install_codex_legacy_cleanup`, `test_startup_bootstrap`, `test_prime_eval`, `test_cp1252_robustness`, `test_pilot_backlog_substrate`, `test_worker_anchor_prose::test_mirror_worker`, `test_skill_prose_diet`), all owned by task .5. Every delegation-test failure in the baseline is now gone, and this task introduced no new failure. `uvx ruff@0.16.0 check .` passed.

baseline: red (python3 scripts/run_tests_parallel.py failed pre-edit - inherited propagation failures owned by task .5)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: impl-review - ran (host backend, fresh fable-5 reviewers; round 1 NEEDS_WORK -> fixes aae3920c -> round 2 SHIP)stage: plan-sync - ran (drift: yes; .5 gained agent_docs/local-dev.md sweep + test_model_routing_scaffold.py pin-with-prose note; cross-spec deferred to conductor pre-.5)

## Evidence
- Commits: 72c4e093125635daf9fbfa4ab8384e9a2c9d63f2, aae3920c140c12040cd13b083dded0510f5f1f27
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_ralph_guard test_model_pin_ceremony_prose test_model_routing_scaffold test_hot_path_sweep test_foreground_rule_fences test_flow_config_schema_drift test_removed_delegate_config_advisory -q (OK, 180 tests), python3 scripts/run_tests_parallel.py (suite_rc=1 - failures identical to the pre-edit baseline: dogfood/manifest/mirror propagation owned by task .5; every delegation-test failure cleared), uvx ruff@0.16.0 check . (All checks passed), impl-review: host backend round 1 NEEDS_WORK (2 findings), round 2 SHIP after fixes (reviewer claude-fable-5, fresh subagents; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.4.json), fix verify: cd plugins/flow-next/tests && python3 -m unittest test_work_argument_literal test_ralph_guard -q (100 tests OK); uvx ruff@0.16.0 check (clean)
- PRs:
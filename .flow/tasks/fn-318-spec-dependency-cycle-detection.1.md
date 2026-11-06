---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-318-spec-dependency-cycle-detection.1 Implement Spec dependency cycle detection

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`flowctl spec add-dep` refuses an edge that closes a dependency cycle, a self-dependency included. It writes nothing and names the path, with code `dependency_cycle` and a `cycle` list. The cycle check and the write share a repo-wide lock, so two concurrent reverse edges cannot both pass.

`validate --all` lists every simple cycle already on disk once, in `spec_cycles` and as root errors. The walk stays fast on acyclic graphs, and a malformed dependency list stays out of it.

Capture's split proposal checks the proposed edges before creating any spec.

`/flow-next:deps` phases chains of any depth and gives every deadlocked spec a cause: `cycle` (with its path), `missing` or `blocked`.

Docs, CHANGELOG, the Codex mirror and the tracker manifest are updated. Tests are in `tests/test_spec_dep_cycles.py`.

stage: impl-review - ran (codex, 3 rounds: NEEDS_WORK -> NEEDS_WORK -> SHIP; the capture prose-test finding was declined under G2 and accepted by the reviewer) (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: a9d75d230c584cd59c0475f35c257143e3cecb4c, 203eeae3ccfe5a7e98f66ad18f5fb1a51d79dd94, 47974a5dc09d72503693d93e368ae54e402d4912
- Tests: python3 scripts/run_tests_parallel.py
- PRs:
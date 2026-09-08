---
satisfies: [R1, R2, R3, R4]
---
# fn-224-refactorpython-remove-dead-paths-and.1 Review and simplify Python with regression evidence

## Description
Review core CLI, review dispatch, tracker integration, supporting tools, and test/evaluation infrastructure using GPT-6 Astra subagents. Implement only grounded deletions, simplifications, and reproduced fixes. Files: Python production code and focused tests; generated manifests/mirror only through generators. Record accepted/rejected findings and run focused suites plus python3 scripts/run_tests_parallel.py and uvx ruff@0.16.0 check .

## Acceptance
R1-R4 satisfied; Python changes preserve public contracts and prompt bytes, reproduced bugs have regression coverage, full repository checks pass, required generated artifacts are idempotent. G1/G2 apply.

## Done summary
### Result

Five GPT-6 Astra subagents reviewed the Python CLI, backend dispatch, tracker package, supporting tools, and test/evaluation infrastructure. Implemented the confirmed findings and retained the components whose distinct contracts justify their complexity. Skill prose and emitted review prompts are unchanged.

### Changes

- Core CLI: removed the single-implementation StateStore abstract class and the shadowed timestamp parser; consolidated raw config reads through one reader and the existing snapshot; separated ownership transfer from claim-note selection so force plus a custom note assigns the current actor.
- Review dispatch: removed unused prompt_fit/display_name registry fields and the unused third re-review prompt result; resolved receipt model/effort once while retaining Codex-specific rebinding.
- Tracker: skipped credential resolution for anonymous HTTP; remembered reversible Jira Basic credentials for redaction; rejected symlinked chart-lock parent directories; deleted two helpers with no callers.
- Supporting tools: fixed commented TOML table and array-table boundaries in hook normalization; removed an unconditional newline branch; replaced separate Cursor roster/hash checks with complete copied-file comparison; deleted an unreachable second permission-validation loop while retaining mapped-key enforcement.
- Evaluation checks: measured required files now determine route accuracy, preventing missing common/backend files from producing a successful smaller-candidate verdict. A missing root continues to raise FileNotFoundError.
- Test cleanup: the deliberately failing-kill fixture now registers parent-process cleanup immediately on launch, alongside its existing descendant cleanup. This prevents each suite run from leaving a sleeping orphan shard.
- Added focused behavioral regressions, regenerated distribution hashes, and recorded user-visible fixes under Unreleased. No version bump.

### Regression evidence

New tests failed before their fixes for forced takeover with a custom note, anonymous credential resolution, encoded Basic redaction, both tracker lock entry points through a symlinked directory, missing/extra nested Cursor payload files, and missing required evaluation references. TOML failures were reproduced directly; tests cover valid parse results, preservation of unrelated content, and idempotency.

Focused suites cover config fallbacks and sentinel semantics, task ownership, chart claims/locks, tracker executor/conformance/state, backend resolution, convergence caps/journals, prompt pins, no-embed dispatch, real Codex installation, Cursor payload verification, OpenCode permissions, and evaluation route measurement. The real Codex installer test passed after distribution regeneration.

Two Codex sync runs passed their guards and produced identical output with no mirror diff. Repository-wide Ruff, diff whitespace, and spec validation passed. The full parallel suite passed 4,806 tests across 207 files, with 7 skips, zero failures, and zero errors. An initial full run caught a test-loader guard mismatch in the new Cursor test; switching to a normal scoped import fixed it, and the fresh full run passed. Post-run inspection found two orphan timeout-test parents from those runs; their exact temporary-corpus identities were verified before termination, and the fixture cleanup was fixed separately. All 30 affected runner tests passed afterward; process inspection found no remaining synthetic timeout shards, and the repository-wide Ruff check passed again.

### Review disposition

- Retained the shared backend driver; provider-specific transport, resume, effort, and sandbox handling have actual consumers. The old generic-runner backlog description predates the current shared implementation.
- Retained journal recovery, transaction locks, no-clobber publication, chart serialization, and ownership checks. Architectural extraction remains separate backlog work.
- Retained legacy persisted-layout normalization and tracker aliases. They support existing data rather than speculative compatibility.
- Retained separate empty-object lookup semantics; merging both lookup helpers would change behavior.
- Retained provider-specific status/resolution, claim ledgers, pagination bounds, test-runner process containment, Ralph guard parsing, bootstrap fast paths, and config ownership validation.
- Preserved historical eval fixtures and negative results. A fixture-only skill-prose reduction assertion was noted but left outside this Python-product cleanup.
- Astra peer review checked other agents' changes; this is a same-family second opinion, not a recorded cross-family implementation gate.

### Delivery scope

R1-R4 and G1/G2 addressed. The downstream documentation walk found existing command and safety contracts already describe the intended behavior; this PR restores them and changes no workflow, public configuration, or release version. Customer release announcements remain part of the separately authorized release. No live tracker mutations or external model evaluations ran.
## Evidence
- Commits: b2969ec2b5385a3ee7c1896a7ecd6b99f118899f, 8193465f791a0e9862d0c9e72ee8e8e9ad498ea8
- Tests: python3 scripts/run_tests_parallel.py: 4806 tests across 207 files; 0 failures, 0 errors, 7 skips, python3 -m unittest discover -s plugins/flow-next/tests -p test_run_tests_parallel.py: 30 passed after subsequent fixture-only cleanup; no orphan synthetic shards remain, uvx ruff@0.16.0 check .: passed after final edit, python3 scripts/gen_tracker_manifest.py and ./scripts/sync-codex.sh twice: passed; identical generated output, no Codex mirror diff, Focused pre/post regression suites passed, including real Codex installation (13 tests), prompt pins, no-embed dispatch, tracker execution, TOML preservation, Cursor payload and eval measurement checks, git diff --check and flowctl validate --spec fn-224-refactorpython-remove-dead-paths-and --json: passed
- PRs:
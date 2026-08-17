# fn-199-issue-sweep-pilot-worktreereused-branch.4 Unwedge refunded review journals + drop fn-197 stowaway artifacts

## Description
Two fixes surfaced during this spec's own run.

1. flowctl review-rounds record: a transport-classified record (no parseable verdict) writes a write-ahead journal with receipt/digest legs 'pending', but receipt publication and digest attach are verdict-only by design (_journal_digest_backfill_row fail-closes on transport rows), so the journal can never complete and every later increment on that scope dies REPLAY_REQUIRED - unrecoverable even via spec reset-review-rounds. Fix BOTH ends: (a) creation-time - when outcome != verdict, journal receipt/digest legs are not_applicable (a refunded row publishes nothing; the attempt row fully records the refund), so record's own tail completes and cleans the journal; (b) self-heal - _complete_review_journal treats a pending digest/receipt leg on a no-verdict journal as not_applicable, so repos already wedged by pre-fix journals recover on the next increment without hand-editing .flow state.

2. Remove the fn-197 stowaways committed by this spec's plan commit via git add -A: .flow/artifacts/fn-197-copy-less-installs-resolve-flowctl-from/pr-cognitive-aid/{.write.lock, fn-197-...-pr-aid-6419480c.json} (pr-aid artifacts are local-only by design; the lock is stale runtime state).

Tests (G2): transport-failure record leaves no journal and a follow-up increment reserves cleanly; a hand-written pre-fix wedged journal (digest pending, no verdict, no attachable container) self-heals on increment (no REPLAY_REQUIRED, journal cleaned, attempt-row legs retired). CHANGELOG Unreleased Fixed entry. flowctl.py change: gen_tracker_manifest + sync-codex x2 + focused suites + full gate before push.

## Acceptance
A no-verdict record completes its own journal (no .flow/review-runs residue) and never blocks later increments; an existing wedged journal self-heals on the next increment; both behaviors test-pinned. fn-197 artifact + lock removed from the branch. CHANGELOG Unreleased updated. Manifest regen + sync-codex idempotent + full suite + ruff green.

## Done summary
Fixed the review-round wedge found while dogfooding this spec's own pipeline: a transport-refunded record (no parseable verdict) wrote a finalization journal with pending receipt/digest legs that could never complete (publication and digest attach are verdict-only by design), so every later increment on the scope died REPLAY_REQUIRED, unrecoverable even via spec reset-review-rounds. Refunded journals now retire those legs at creation and record cleans up after itself; _complete_review_journal self-heals pre-fix wedged journals invisibly (same call reserves - no phantom VERDICT=UNKNOWN replay). Host review workflows (impl/plan/completion) now attach findings only on a delivered verdict, mirroring RP. Also dropped the fn-197 pr-aid artifact + stale .write.lock stowaways and gitignored .flow/artifacts/*/pr-cognitive-aid/ (local-only by make-pr design; pre-rule files grandfathered). Regression tests verified to fail against the pre-fix flowctl.

stage: impl-review - ran (model: claude-fable-5, host backend, round 1 SHIP; considers 1-3 applied, 4 declined - a payload cross-check would recreate an unrecoverable wedge for corrupted journals)
## Evidence
- Commits: c208a1db, 1921f086, consider-polish commit (see git log)
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_journal test_review_convergence_cap test_tracker_distribution test_startup_bootstrap -q (353 tests OK), regression tests verified to FAIL against pre-fix flowctl (scratch layout, 1 failure + 1 error), python3 scripts/run_tests_parallel.py (4381 tests OK) + uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent) + gen_tracker_manifest.py
- PRs: https://github.com/gmickel/flow-next/pull/358
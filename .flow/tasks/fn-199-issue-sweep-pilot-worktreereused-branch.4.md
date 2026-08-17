# fn-199-issue-sweep-pilot-worktreereused-branch.4 Unwedge refunded review journals + drop fn-197 stowaway artifacts

## Description
Two fixes surfaced during this spec's own run.

1. flowctl review-rounds record: a transport-classified record (no parseable verdict) writes a write-ahead journal with receipt/digest legs 'pending', but receipt publication and digest attach are verdict-only by design (_journal_digest_backfill_row fail-closes on transport rows), so the journal can never complete and every later increment on that scope dies REPLAY_REQUIRED - unrecoverable even via spec reset-review-rounds. Fix BOTH ends: (a) creation-time - when outcome != verdict, journal receipt/digest legs are not_applicable (a refunded row publishes nothing; the attempt row fully records the refund), so record's own tail completes and cleans the journal; (b) self-heal - _complete_review_journal treats a pending digest/receipt leg on a no-verdict journal as not_applicable, so repos already wedged by pre-fix journals recover on the next increment without hand-editing .flow state.

2. Remove the fn-197 stowaways committed by this spec's plan commit via git add -A: .flow/artifacts/fn-197-copy-less-installs-resolve-flowctl-from/pr-cognitive-aid/{.write.lock, fn-197-...-pr-aid-6419480c.json} (pr-aid artifacts are local-only by design; the lock is stale runtime state).

Tests (G2): transport-failure record leaves no journal and a follow-up increment reserves cleanly; a hand-written pre-fix wedged journal (digest pending, no verdict, no attachable container) self-heals on increment (no REPLAY_REQUIRED, journal cleaned, attempt-row legs retired). CHANGELOG Unreleased Fixed entry. flowctl.py change: gen_tracker_manifest + sync-codex x2 + focused suites + full gate before push.

## Acceptance
A no-verdict record completes its own journal (no .flow/review-runs residue) and never blocks later increments; an existing wedged journal self-heals on the next increment; both behaviors test-pinned. fn-197 artifact + lock removed from the branch. CHANGELOG Unreleased updated. Manifest regen + sync-codex idempotent + full suite + ruff green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

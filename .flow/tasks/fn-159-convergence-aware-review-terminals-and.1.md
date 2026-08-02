---
satisfies: [R1]
---
# fn-159-convergence-aware-review-terminals-and.1 flowctl: artifact-hash dispatch guard, --force, reset clears baseline

## Description
flowctl foundation for the convergence terminals: hash epoch, id-keyed reservation registry + durable finalization journal, cross-process locking with a fixed lock order, idempotent delivered-verdict replay, and system-owned SHIP reset. flowctl + tests ONLY — no workflow-file or skill-prose edits (those are .7).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_review_convergence_cap.py`

### Approach
- **Epoch:** `review_hash_epoch` map on spec state, exact shape `{"plan": int, "impl:<canonical-task-id>": int}` (absent key = 0); attempt rows stamped `hash_epoch` at reservation. ALL reset paths advance the matching scope(s) — `--impl` bulk reset advances every `impl:*` epoch it wipes: `cmd_spec_reset_review_rounds` (:26597), `cmd_review_rounds_reset` (:26707), and the SHIP reset — which becomes system-owned: `review-rounds record` atomically resets counter + advances epoch on SHIP (extend the folded reset; preserve fn-134.7/R22: `reset_review_cap` never touches `review_pending_rounds`).
- **Reservation registry:** `review-rounds increment` returns a reservation id; metadata `{artifact_sha256: string|null, forced: bool, epoch: int, review_type: string}` persisted keyed by id alongside the pending count. `record --reservation-id` consumes it onto the attempt row (verdict AND refund); UNKNOWN supplied id → always exit 2, zero mutation; OMITTED id → accepted only when exactly one reservation is pending in the requested scope (metadata consumed implicitly), otherwise exit 2 zero mutation; tests for zero/one/multiple pending — keeps un-migrated serial RP fences working during the .1→.7 window without weakening out-of-order ownership. Attempt rows stamped `reservation_id` at finalize.
- **Finalization journal (durable, authoritative):** before consuming a reservation, write a per-reservation journal under `.flow/review-runs/` as a complete write-ahead operation: response text + checksum, the exact intended receipt payload (session/model/effort, backend spec, focus/base metadata, tallies, timestamp), the validated findings container + prior-lineage identity, receipt target, scope/type, SHAs, verdict, status target. Cleared only after all applicable legs complete. The pre-increment gate scans JOURNALS (not just attempts) and reconciles each with reservations/attempts — an unconsumed journal resumes finalization, never permits dispatch. Named tests: journal-written/attempt-not-created boundary; byte-equivalent receipt replay after restart and after receipt-pointer advance.
- **Progress states:** attempt-row `finalized: {receipt, digest, status}` each `pending | complete | not_applicable` (`not_applicable` at creation for legs the surface lacks — standalone reviews never block on a status leg).
- **Idempotent replay:** every finalization write carries reservation identity; exact-match already-applied write = successful no-op. Crash boundaries tested in a fresh process with the /tmp response deleted: receipt-published/progress-unmarked; digest-written/receipt-missing.
- **Any-incomplete gate:** new reservation refused while ANY consumed-verdict attempt in scope has a `pending` leg; replay them first (zero dispatch). Status-write surfaces gain `--reservation-id`, require exactly one matching attempt.
- **Locks:** one sidecar-scoped flock under `.flow/locks/` wraps reserve/finalize/refund/resets/backfill; for two-resource ops the order is RECEIPT lock BEFORE SIDECAR lock, held from lineage validation through sidecar mutation + receipt publication.
- Guard/hash-comparison logic itself, per-transport reserve points, workflow fences, and the NOT_RETRYABLE marker live in .7 — this task lands the state machinery they call. **.1 and .7 are one indivisible landing unit on the spec branch** (no intermediate state reaches main); the exactly-one-pending id-less path keeps RP operational between the two commits.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:9282-9545` — record/finalize/refund/reset paths
- `plugins/flow-next/scripts/flowctl.py:26597-26800` — reset/increment/record CLI verbs
- `plugins/flow-next/scripts/flowctl.py:35715-35850` — receipt write + status map (receipt-lock interplay)
- `plugins/flow-next/tests/test_review_convergence_cap.py:208` — TestDeterministicCap conventions

**Optional:**
- `.flow/locks/` usage elsewhere in flowctl (grep `flock|locks/`) — existing lock idioms

### Key context
- Refund arithmetic and pending-count semantics unchanged throughout.
- Overlapping-process tests (two concurrent increments; record racing reset) — truly concurrent, not sequential.
- SHIP/NEEDS_WORK replay tests live here; NEEDS_HUMAN replay tests land with .3 (verdict doesn't exist yet).

### Acceptance
- [ ] Epoch advanced by all three reset paths; SHIP reset system-owned in record; pending invariant intact
- [ ] Reservation id round-trips increment→record; unknown id exit 2 no-mutation; out-of-order/duplicate/concurrent finalize tests
- [ ] Journal durable under `.flow/review-runs/`; replay works in a fresh process with /tmp response deleted
- [ ] Idempotent replay at both crash boundaries; any-incomplete gate refuses new reservations and replays first
- [ ] Lock + lock-order contract enforced; overlapping attach-vs-finalize test scaffolding in place
- [ ] Focused suite green: `python3 -m unittest test_review_convergence_cap -q`

### Round-7 additions
- **Journal complete pre-consumption on every path:** `record` gains receipt/status-target parameters, constructs + journals the exact receipt operation and validated findings container BEFORE consuming the reservation; `attach` publishes/backfills FROM the journal, never re-derives. Named test: fresh-process crash after record, before the attach input file exists.
- **Typed recovery result (plural — round 8):** replay returns exit 0 JSON `{replayed: true, replays: [{reservation_id, verdict}, ...]}`, no reservation created, no dispatch until every in-scope journal is complete; terminal precedence NEEDS_HUMAN > NEEDS_WORK > all-SHIP; per-verdict + mixed-verdict (two incomplete journals) tests prove zero dispatch (NEEDS_HUMAN leg lands with .3).
- **`finalized.digest` = operation completion, not digest presence:** a successful validated parse yielding absent/legacy/unsupported findings marks the leg `complete`; only interrupted/failed operations stay `pending`. Malformed/legacy/no-findings recovery tests.

### Round-8 additions
- Container construction ownership is SINGULAR: `record` constructs + journals the receipt operation and findings container pre-consumption; `attach` ONLY validates and publishes the journaled payload by reservation id (the earlier "attach enriches" instruction is superseded).
## Acceptance
- [ ] Foundation half of R1 (epoch, reservations, journal, replay, locks) proven by tests; no workflow files touched
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

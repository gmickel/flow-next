---
satisfies: [R2, R4]
---
# fn-159-convergence-aware-review-terminals-and.2 flowctl: stall detector on findings lineage + ratchet reads structured items

## Description
**Depends on:** .1 (reservation registry, journal, locks) and .7 (workflow fences, guard wiring) — encoded in flowctl deps; numeric suffix order is not execution order.

Build the deterministic stall detector on spec-state findings digests (persisted at record time), and switch the convergence ratchet to render `findings.items` instead of the 8000-char prose blob.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, plan/impl/completion `workflow-rp.md` (attach fences) AND `workflow-host.md`, `plugins/flow-next/tests/test_review_convergence_cap.py`

### Approach
- **Digest persistence — ONE authoritative construction point (round-2 P1: in-process handlers finalize BEFORE receipt write; RP records BEFORE `review-findings attach`):** the digest derives from the SAME `build_review_receipt_findings` container the receipt gets. In-process: build container first, pass digest+container into finalize/receipt-write together. RP: `review-findings attach` gains `--reservation-id` and backfills the digest onto the attempt row STAMPED with that id (stamped at finalize by .1) — requires exactly one matching consumed-verdict row with matching scope+backend+reviewKind; unknown, duplicate, transport-failure, or conflicting attachments fail with ZERO mutation; all three workflow-rp.md attach fences pass the id. Assertion test: receipt findings and attempt digest derive from one container.
- **Digest shape with provenance (round-2 P1: `introduced` ≠ round-newness):** ≤40 items × {findingId, chainRoot (derived across priorFindingId/supersession hops at container build), severity, status, classification, firstSeenThisRound}, plus digest-level backend + reviewKind; >40 → `digest_truncated: true` (inert round).
- **Detector** runs in `enforce_and_increment_review_cap()` after the .1 hash guard: read the last 2 consecutive consumed verdict rounds in the same counter scope AND current `hash_epoch` from spec state. Both must carry non-truncated digests; otherwise inert (identical to today — never a false stall).
- Rules (any fires → `ESCALATE: review loop stalled (<rule>)`, exit REVIEW_CAP_EXIT_CODE 4, reuse cap-stanza shape :9472-9500, idempotent, no increment):
  (a) same chainRoot `not_fixed` in both rounds — identity rule: requires both digests share backend+reviewKind (unlinked transition → inert);
  (b) flat trajectory — worst open severity fails to strictly improve AND open count fails to strictly decrease. EXACT MATH (review P1 — `_FINDINGS_SEVERITY_ORDER` P0→0…P3→3; naive max() inverts): worst = MIN numeric rank over open items (status open/not_fixed); improves iff current worst rank > prior worst rank; EMPTY open set = converged, rule can never fire;
  (c) `firstSeenThisRound && introduced` at rank <=1 (P0/P1) in each of the 2 rounds — identity rule, same backend+reviewKind requirement; aggregate rule (b) stays live across switches.
- **Ratchet:** `build_convergence_ratchet_block` (:9598) gains a structured path — sibling of `_read_prior_findings` (:9547) returning `findings.items`; render a numbered list (ordinal, severity, classification, status, title, file:line). **Cursor path is budget-aware (round-2 P1):** derive a character budget from actual remaining cursor capacity (:36218-36225 fitter runs after prompt join) and append only whole items while the next complete item + closing delimiter fit; tests: max-length titles/paths, nearly exhausted prompt, item/delimiter integrity. Prose path stays as labeled legacy fallback. Preserve injection-neutralization (:9621-9626) — neutralize inside rendered item text too.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:9670-10062` — record path where the digest is built (post-.1 shape: `_record_review_attempt_locked`, `_complete_review_journal`, `review_replay_terminal_verdict`)
- `plugins/flow-next/scripts/flowctl.py:5322-5450, 5783-5900` — findings validator + container shape (unaffected by .1's line shift, not yet re-verified)
- `plugins/flow-next/scripts/flowctl.py:10335-10429` — `_read_prior_findings` (:10335) and `build_convergence_ratchet_block` (:10386, still prose-blob-only signature — `prior_findings: Optional[str]` — pre-.2), rereview preamble <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.1 shifted this region ~788 lines forward (was :9547-9700); anchors corrected -->
- `plugins/flow-next/tests/test_review_convergence_cap.py:84` — TestConvergenceRatchet conventions

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:36160-36230` — cursor argv-budget path
- `.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md` — receipt-reinforced confabulation lesson

### Key context
- A `--force`d round is a normal detector input. Rounds without digests break consecutiveness (inert).
- Detector reads spec state ONLY — no receipt I/O at enforce time; backend/type/session switches don't restart lineage.
- Severity transition tests required: P0→P1 (improves), P1→P2 (improves), P2→P1 (regresses), empty-open-set (converged).

### Acceptance
- [ ] Digest persisted from the SAME container as the receipt (assertion test); provenance fields present; truncation flagged; malformed/absent → no digest
- [ ] Each rule fires on a crafted 2-round digest pair; none fires across epoch boundary, digestless round, or (for identity rules) a backend/type switch; three-round newness + carried-introduced + multi-hop supersession tests
- [ ] Severity math: MIN-rank worst, all four transition tests, empty-open-set never stalls
- [ ] Stall exit 4 + stalled marker; counter/pending untouched
- [ ] Ratchet renders numbered structured items; prose fallback labeled; injection tests pass
- [ ] Focused suite green: `python3 -m unittest test_review_convergence_cap -q`

### Round-3 additions
- Digest exact public shape (API contract): `{backend, reviewKind, digest_truncated, items:[{findingId, chainRoot, severity, status, classification, firstSeenThisRound}]}` — `chainRoot` is the only chain-identity name; validate every provenance field at write.
- Backfill runs under the .1 sidecar lock.
- Host path: inventory the per-surface workflow-host.md dispatch fences; add a host-path structured-ratchet regression (host is NOT covered by `cmd_backend_review`).

- Round-4: backfill participates in the finalization-progress contract (`finalized.digest`); attach under receipt-before-sidecar lock order; replay path re-runs backfill from the on-disk response without dispatch.
## Acceptance
- [ ] R2 satisfied (digest-based, exact severity math, fail-inert matrix)
- [ ] R4 satisfied (structured render + legacy fallback + neutralization)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

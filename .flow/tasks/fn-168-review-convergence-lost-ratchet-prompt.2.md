---
satisfies: [R1, R2, R8]
---
# fn-168-review-convergence-lost-ratchet-prompt.2 Aggregate all-clear record semantics + production-path fixtures

## Description
Implement the aggregate all-clear record's *semantics* — the scoped sweep of carried priors — plus the R8 carried-status reset, both in the same single parse pass as the per-ordinal records, and pin the behavior with production-parser fixtures plus the `unaddressed: []` negative test.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_review_finding_prior_items`), `plugins/flow-next/tests/test_review_findings_parser.py`, `plugins/flow-next/tests/test_review_findings_fixture_corpus.py`, `optimization/reached-path/fixtures/review-findings/v1/<backend>/*.md` + `INDEX.json` (repo root, all 6 backends), `.flow/bin/flowctl.py` (propagation)

### Approach
- **Precondition: `.1`'s vocabulary/recognition work must already be in the tree.** Re-verify before starting — run the aggregate line through `_FINDINGS_PRIOR_RE` and `_FINDINGS_PRIOR_RECORD_RE` and confirm counts match. If it still mismatches, stop: implementing sweep semantics on top of a container that gets dropped to `None` proves nothing.
- Implement the sweep in `_review_finding_prior_items`: an aggregate `Prior findings: all fixed` record marks every carried prior currently `open`/`not_fixed` as `fixed`. Scope rules, all required:
  - fires **only** when the prior set is non-empty (round 1 never activates it);
  - sweeps **only** items currently `open` or `not_fixed`;
  - **never** `withdrawn` — that is a resolved-differently terminal, and re-stamping it `fixed` would corrupt lineage;
  - **any** explicit per-ordinal record disables the aggregate path entirely (explicit beats implicit) — **enforced by parse order, not just documented**.
- Evaluate the aggregate record in the **SAME single pass** as the per-ordinal records over the same line family, so a malformed stray line stays recognized-but-invalid (whole-container `None`) and can never read as a clean aggregate round. This is the fn-136 memory contract (`structured-review-parsers-must-2026-07-30`): separate presence detection from canonical parsing; recognized-but-invalid must select the invalid sentinel, never the absent sentinel.
- **R8 — reset carried `not_fixed` to `open` before applying this round's records (plan-review round 1, P0).** Verified: the carry-forward deep-copy in `_review_finding_prior_items` copies `status` **verbatim**, and only ordinals matched *this* round get overwritten. So a prior explicitly marked `not-fixed` in round 2 and then merely omitted in round 3 sits at `not_fixed` in BOTH digests, and `same-not-fixed-lineage` escalates on a round that said nothing — the exact silent false-stall this spec deletes, surviving inside the survivor. The reset makes the spec's central claim literally true: the lineage intersection now requires an explicit `not-fixed` in **both** consecutive rounds.
  - Scope: `not_fixed` → `open` only. **Preserve `fixed` and `withdrawn`** — they are resolved terminals, and re-opening them would corrupt lineage and re-raise findings the reviewer already closed.
  - Ordering: reset first, then apply the round's per-ordinal records and the aggregate sweep, all inside the existing single pass. A count mismatch must still return whole-container `None` exactly as today.
  - Round 1 has no carried items, so the reset is a no-op there.
  - Accepted cost (spec Boundaries (e)): the ratchet prompt then renders such an item as `open` rather than `not_fixed`, losing the "you called this unfixed last round" nuance in the status column. That is prompt copy, not evidence; do NOT add a per-round-verification digest field to recover it.
- **Negative test pinning that `unaddressed: []` alone is NOT a prior-findings signal.** This is not a stylistic preference — it is the load-bearing invariant of the whole spec. `unaddressed` rides in the canonical closing JSON tail of *every* review (observed live: a round-1 plan review emitted `"unaddressed":["R1","R3","R6"]` before any prior finding existed, and a round-3 SHIP emitted `"unaddressed":[]` with zero discussion of priors). Since `.3` leaves `same-not-fixed-lineage` as the only stall class and it reads exclusively `not_fixed`, an ambient signal sweeping priors to `fixed` would erase the only evidence stall detection has left.
- Table-test the contradiction cases: aggregate + a contradicting per-ordinal `not-fixed` → the explicit line wins; malformed stray line + aggregate → recognized-but-invalid, never a silent all-clear.
- **Fixture corpus lives at REPO ROOT**: `optimization/reached-path/fixtures/review-findings/v1/<backend>/*.md` + `INDEX.json` — **not** under `plugins/flow-next/`. A new case must land in `CASES` (in `test_review_findings_fixture_corpus.py`) **AND** `INDEX.json` for **all 6 backends** (codex, copilot, cursor, host, rp, export) or the matrix test hard-fails.
- Tests drive the **production parser** end to end, never hand-built container dicts (memory `test-production-path-not-parallel-construction-2026-05-21`).
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `_review_finding_prior_items` (~:5134-5207): the record/canonical counting, the carry-forward deep-copy, the single-item no-ordinal special case (~:5171), and the `None` return; sole call site ~:5476
- `plugins/flow-next/scripts/flowctl.py` — `_FINDINGS_STATUS_ALIASES` (~:4577) / `_FINDINGS_PRIOR_RE` (~:4625) / `_FINDINGS_PRIOR_RECORD_RE` (~:4639) as `.1` left them
- `plugins/flow-next/tests/test_review_findings_fixture_corpus.py` (matrix ~:37) and `optimization/reached-path/fixtures/review-findings/v1/INDEX.json` — the 6-backend contract before adding any case
- `plugins/flow-next/tests/test_review_findings_parser.py` (grammar accept/reject ~:368-437) — the table-test style to follow

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py` — `extract_review_json_block` (~:6626-6657), `_unaddressed_from_json` (~:6719-6731): what the `unaddressed` key actually is, for the negative test's docstring
- `plugins/flow-next/scripts/flowctl.py` — `build_review_findings_digest` (~:5954-5984) for the row shape the swept statuses feed

### Key context
- `status: "open"` is written ONLY at creation (~:4920, :5540, :5123). Carry-forward deep-copies untouched and only an explicit resolution writes `fixed`/`not_fixed`/`withdrawn`. The aggregate sweep is the one new writer of `fixed` on carried items — keep that property true and stated, because `.3`'s surviving stall class depends on `not_fixed` being explicit-only.
- No new receipt-schema fields and no digest-shape change.
- Round-1 reviews and legacy receipts (no container, or a pre-change container) keep today's behavior — regression-test it.

## Acceptance
- [ ] `.1`'s vocabulary precondition re-verified before implementation (aggregate line produces no RECORD/PRIOR count mismatch); noted in the done summary
- [ ] Aggregate `Prior findings: all fixed` marks carried priors at `open`/`not_fixed` as `fixed`, evaluated in the SAME pass as per-ordinal records
- [ ] `withdrawn` items are never swept; the path never fires on an empty prior set; any per-ordinal record disables it, enforced by parse order
- [ ] Malformed stray line + aggregate → recognized-but-invalid (whole-container `None`), never a silent all-clear; aggregate + contradicting per-ordinal `not-fixed` → the explicit line wins
- [ ] Negative test: `unaddressed: []` alone does NOT mark any prior finding `fixed`, with a docstring stating why (ambient JSON-tail key, emitted even in round 1)
- [ ] A codex-style compliant response yields correct `fixed` / `not_fixed` statuses in the receipt findings container **via the production parser** (R1's fixture half)
- [ ] New fixture cases registered in `CASES` **and** `INDEX.json` for all 6 backends; `test_review_findings_fixture_corpus` green
- [ ] R8: a carried item at `not_fixed` is reset to `open` before this round's records are applied; `fixed` and `withdrawn` are never re-opened; round 1 is a no-op
- [ ] R8 tested via the production parser: explicit `not-fixed` in two consecutive rounds keeps both digests at `not_fixed`; explicit in round 2 then omitted in round 3 leaves round 3 at `open`
- [ ] Round-1 / legacy-receipt behavior unchanged, regression-tested
- [ ] Focused suites green: `python3 -m unittest test_review_findings_parser test_review_findings_receipts test_review_findings_fixture_corpus test_review_convergence_cap -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

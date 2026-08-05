---
satisfies: [R1, R2]
---
# fn-168-review-convergence-lost-ratchet-prompt.2 Parser: dedicated aggregate all-clear, scoped; production-path fixtures for both paths

## Description
Teach the parser the dedicated aggregate all-clear record, correctly scoped, and prove both the per-ordinal path (R1's test half) and the aggregate path (R2) against the production parser plus the 6-backend fixture corpus.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_FINDINGS_PRIOR_RE`, `_FINDINGS_STATUS_ALIASES`, `_review_finding_prior_items`), `plugins/flow-next/tests/test_review_findings_parser.py`, `optimization/reached-path/fixtures/review-findings/v1/<backend>/*.md` + `optimization/reached-path/fixtures/review-findings/v1/INDEX.json` (**repo root — NOT under `plugins/flow-next/`**; all 6 backends), `plugins/flow-next/tests/test_review_findings_fixture_corpus.py`, `.flow/bin/flowctl.py` (propagation)

### Approach
- **Vocabulary + line recognition are a PRECONDITION delivered by task .1** (hyphenated `not-fixed` accepted, aggregate line recognized without a count mismatch). Re-verify that precondition holds before starting; this task adds the aggregate's SEMANTICS on top of it.
- Implement the aggregate's effect: a recognized `Prior findings: all fixed` with zero per-ordinal records marks the carried priors fixed, evaluated in the SAME one pass as the per-ordinal records so a malformed stray line stays a recognized-but-invalid signal (whole-container `None`) and can never be mistaken for a clean aggregate round.
- Scoping rules, all required: fires only when the prior set is non-empty; sweeps only items currently `open` or `not_fixed`; **never** touches `withdrawn`; any per-ordinal record present disables the aggregate entirely (explicit beats implicit — make the parse order enforce this, not just document it).
- `unaddressed: []` must NOT become a prior-findings signal — add the negative test that pins this (a response with `unaddressed: []` and no prior-finding line carries forward unchanged).
- Fixture corpus: add the new case(s) to `CASES` in the test AND `INDEX.json` `cases`/`expectations` for ALL 6 backends (codex, copilot, cursor, host, rp, export) in the same change, or the matrix test hard-fails. Match the existing fn-136 fixture format exactly.
- Tests drive the production parser end to end (memory `test-production-path-not-parallel-construction`): no hand-built container dicts standing in for parser output. Table-test R2's matrix: aggregate-only / aggregate+contradicting-explicit / per-ordinal-only / neither / withdrawn-present / empty-prior-set.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `_review_finding_prior_items` (~:5134-5207) incl. the RECORD/PRIOR count-mismatch `None` branch and the carry-forward comment; call site ~:5476 for what `None` costs
- `plugins/flow-next/scripts/flowctl.py` — the regex family + `_FINDINGS_STATUS_ALIASES` (~:4577-4648)
- `plugins/flow-next/tests/test_review_findings_parser.py` (~:368-437) — the existing accept/reject grammar tests to sit beside
- `plugins/flow-next/tests/test_review_findings_fixture_corpus.py` (~:11, matrix ~:37) + `INDEX.json` — the corpus contract

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py` — `extract_review_json_block` / `_unaddressed_from_json` (~:6626-6731), only to confirm the `unaddressed` path stays untouched
- `plugins/flow-next/tests/test_review_findings_receipts.py` — if an end-to-end receipt assertion is cheap to add

### Key context
- The aggregate signal is NOT `unaddressed: []` — the spec's original trigger was replaced at plan time because R-ID coverage and finding resolution are orthogonal (see the spec's R2 amendment). Do not re-derive; do not wire the JSON tail into this parser.
- Status vocabulary is fixed by `_FINDINGS_STATUS_ALIASES`; an out-of-vocabulary word must keep failing closed rather than silently vanishing (fn-136 memory class).
- Depends on .1 having settled the exact prompt wording so fixtures assert the real contract.
## Acceptance
- [ ] Task .1's vocabulary precondition re-verified at start; a compliant aggregate-only response produces no count mismatch AND sweeps (regression-tested)
- [ ] `Prior findings: all fixed` parsed in the same line-start family; per-ordinal records present disable it (enforced by parse order, table-tested)
- [ ] Aggregate sweeps only `open`/`not_fixed`; `withdrawn` untouched; no activation on an empty prior set
- [ ] Negative test pins that `unaddressed: []` alone is NOT a prior-findings signal
- [ ] Malformed stray prior-finding line still fails closed (recognized-but-invalid), never a silent all-clear
- [ ] R1 test half: a codex-style compliant response yields correct `fixed`/`not_fixed` statuses through the PRODUCTION parser
- [ ] Fixture corpus case(s) added under the REPO-ROOT `optimization/reached-path/fixtures/review-findings/v1/` (`CASES` + `INDEX.json`) for all 6 backends; matrix test green
- [ ] Focused suites green: `python3 -m unittest test_review_findings_parser test_review_findings_fixture_corpus test_review_findings_receipts test_review_json_tallies -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

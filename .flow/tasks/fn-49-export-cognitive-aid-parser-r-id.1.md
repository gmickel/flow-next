---
satisfies: [R1, R2, R5, R6]
---

## Description

Extend the acceptance-criteria R-ID parser in `plugins/flow-next/scripts/flowctl.py` to recognize suffix forms like `R4a` and `R4b` — currently the regex is `R\d+` and silently drops them. Capture-driven specs that emerge with sub-scoped criteria (e.g. fn-48's `R4a` for Codex mirror prelude / `R4b` for canonical prelude) get correctly counted in `acceptance_count` and `uncovered_r_ids` after this fix.

This is the **early proof point** for fn-49 — single regex extension + lexical-sort check + smoke fixture. Simpler than fn-49.2 (which has implementer-choice fallback design). Validates the test-and-fix loop on the easier bug first.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`cmd_spec_export_cognitive_aid` and/or its acceptance-criteria parsing helper), `plugins/flow-next/tests/test_acceptance_criteria_parser.py` (existing test file — extend with suffix cases), optionally `plugins/flow-next/docs/spec-template.md` (document R<n><suffix> as supported canonical form if blessing the pattern), CHANGELOG.md (release-time entry under `[unreleased]`).

## Approach

- Locate the acceptance-criteria parser. Per `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` memory entry, the relevant function is `_export_parse_acceptance_criteria` in `flowctl.py` (tolerates 3 heading variants since fn-44 / 1.1.4). The R-ID extraction regex is somewhere near it.
- Extend the regex pattern. The simple form is `R\d+[a-z]?` — single lowercase letter suffix. Be deliberate about NOT broadening to digit-suffixes (`R4.1`) or multi-letter (`R4ab`) unless there's a real need; the spec scope is `R4a` / `R4b` only.
- Verify lexical ordering: `R4` (if present) sorts before `R4a` which sorts before `R4b` which sorts before `R5`. Python's `sorted()` over the string IDs already gives this for the suffix case; verify with an explicit test.
- Add unit tests in the existing `test_acceptance_criteria_parser.py` test file (per memory entry, this file already exists from fn-44 work and locks the 3 heading variants). New cases:
  - R1, R2, R4a, R4b, R5 → parser returns all 5 in correct order
  - R1, R4a, R4b → parser returns 3 (no synthetic R4 insertion)
  - Edge: R4 + R4a + R4b coexisting (rare but valid — R4 was the original, then sub-scoped during a revision)
  - Reject: `R4ab` (multi-letter suffix) — out of scope for this fix
  - Reject: `R-4` / `r4` / `r4a` — must remain strict
- Run fn-48 export and confirm `acceptance_count == 9` post-fix (was 7):
  ```bash
  .flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json | jq '.spec.spec_sections.acceptance_criteria[].id'
  ```
- Decide and document whether suffix R-IDs are now officially canonical or just tolerated. If canonical: update `plugins/flow-next/docs/spec-template.md` with a one-line note. If tolerated only: leave docs alone and add a comment in the parser explaining the tolerance scope.
- Draft a `[unreleased]` CHANGELOG bullet under `### Fixed`. Cite fn-48 as the surfacing context.

## Investigation targets

**Required**:
- `plugins/flow-next/scripts/flowctl.py` — find `_export_parse_acceptance_criteria` or equivalent + the R-ID extraction regex. Note: this file is ~22,000 lines; use grep to locate the function.
- `plugins/flow-next/tests/test_acceptance_criteria_parser.py` — existing test file from fn-44; extend with suffix cases.
- Memory entry `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` — parser contract failures from prior cycle; lessons on heading-variant tolerance and `--json` threading apply equally to this regex change.
- `.flow/specs/fn-48-backend-split-review-workflows-flowctl.md` — the spec body that contains R4a and R4b; the fixture this fix is verified against.

**Optional**:
- `plugins/flow-next/docs/spec-template.md` — only touch if blessing R<n><suffix> as canonical format.
- Memory entry `bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08` — adjacent null/missing-field handling lessons.

## Acceptance

- [ ] Regex extended from `R\d+` → `R\d+[a-z]?` in the acceptance-criteria parser; `R4ab` (multi-letter) and `R-4` (separator) reject.
- [ ] Lexical sort preserves `R4` < `R4a` < `R4b` < `R5` ordering across `acceptance_criteria[].id` and `uncovered_r_ids` arrays.
- [ ] Re-running `.flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json | jq '.spec.spec_sections.acceptance_criteria | length'` returns `9` (was 7 pre-fix).
- [ ] Unit tests added in `test_acceptance_criteria_parser.py` covering: all-suffixed, mixed plain+suffixed, R4+R4a+R4b coexistence, rejection of out-of-scope forms.
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` runs green (existing 127/2 baseline preserved + new R-ID-suffix cases pass).
- [ ] Decision documented (in code comment or `docs/spec-template.md`): R<n><suffix> is canonical / tolerated. Either choice is acceptable; just be explicit.
- [ ] CHANGELOG `[unreleased]` entry drafted under `### Fixed` citing fn-48 as surfacing context.

## Done summary
Extended `_export_parse_acceptance_criteria` regex from `R\d+` to `R\d+[a-z]?` so sub-scoped sibling R-IDs (R4a, R4b) are no longer silently dropped. Verified against fn-48 spec: post-fix `acceptance_count` is 9 (was 7); lexical sort preserves R4 < R4a < R4b < R5. Added 8 unit tests in `test_acceptance_criteria_parser.py`, documented suffix form in `templates/spec.md`, re-synced Codex mirror, drafted `[unreleased]` CHANGELOG entry. Full test suite (632) and smoke baseline (127/2) both green.
## Evidence
- Commits: e545ca3736bbbde0d934764c5893b0f88d13d596
- Tests: python3 -m unittest tests.test_acceptance_criteria_parser -v (13 pass), python3 -m unittest discover -s tests (632 pass, 2 skipped), bash plugins/flow-next/scripts/smoke_test.sh (127 pass / 2 fail = pre-existing copilot-CLI baseline), flowctl spec export-cognitive-aid fn-48-... | jq length returns 9 (was 7)
- PRs:
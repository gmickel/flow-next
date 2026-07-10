## Description
Size: M. flowctl.py (dual-copied): four additive export-cognitive-aid fields per epic Architecture §1-4. Deterministic only — no LLM calls, reproducible from repo state.
## Approach
1. `changed_symbols`: parse `git diff --base` hunk headers (`@@ … @@ <ctx>`); dedupe per file; empty when git yields none.
2. `derived`: config leaf `makePr.derivedPaths` (default = flow-next shapes: codex mirror dir, .flow/ state) + byte-identical dual-copy detection via content hash against named source (drifted → NOT derived).
3. `removed_export_refs`: from the diff's removed lines, extract candidate symbol definitions (conservative regex per language of changed files); word-boundary grep repo (excluding the removals themselves); report file:line candidates; bounded cost.
4. `tasks[].evidence.files` surfaced verbatim into the payload.
5. Unit tests per epic R1-R3 cases (fixture diffs); update export docs (flowctl.md).
## Acceptance
- [ ] Epic R1-R4 with tests; additive-only (absent fields = old payload shape); dual-copy parity; full suite + smoke green.

## Done summary
Added the four additive deterministic-traceability fields to `flowctl spec export-cognitive-aid` (flowctl.py, dual-copied): per-file `changed_symbols` from git hunk-header context, `derived` mirror/dual-copy/state classification with hash-verified dual-copy detection + `makePr.derivedPaths` config override, top-level `removed_export_refs` (conservative git-grep scan for deleted symbols still referenced), and `tasks[].evidence.files` surfaced verbatim. All additive (absent = old payload shape, no schema bump); flowctl.md export docs updated; 21 new unit tests across R1-R4; dual-copy parity held; full suite + smoke green.
## Evidence
- Commits: 2547e111216d16c55f45c6a86652584ca4e236d0
- Tests: python3 -m unittest plugins.flow-next.tests.test_export_traceability (21 pass), python3 -m unittest discover -s plugins/flow-next/tests (full suite exit 0), bash plugins/flow-next/scripts/smoke_test.sh (144 passed, 0 failed)
- PRs:
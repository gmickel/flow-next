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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

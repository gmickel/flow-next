I've completed all phases. Let me summarize my findings:

- **Phase 1–3 (drift):** Task `.1`'s implementation is a faithful parity port. Every name/signature the downstream tasks reference matches the spec's declared contract exactly: `run_cursor_exec(prompt, session_id=None, *, spec=None, repo_root) -> (result_text, session_id, exit_code, stderr)`, the `cursor` registry entry (`models` set incl. all 10, `efforts: None`, `default_model: "gpt-5.5-high"`), `require_cursor`/`get_cursor_version`, `cmd_cursor_check` → `{available, version, authed}`, `CURSOR_ARGV_PROMPT_MAX` reuse, positional-argv `--mode ask --trust`, and the explicit prompt-too-large `ValueError`. The only unspecced addition is the internal `_parse_cursor_result` helper — not referenced by any downstream task.
- **Phase 3b.1 (glossary):** 38 terms, but every entry has `avoid: []` — no aliases exist, so no rename is possible.
- **Phase 3b.2 (decisions):** Both active decisions name modules (`plugins/flow-next/docs/platforms.md`; `strategy`) that `.1` did not touch (it touched `flowctl.py` + 2 test files), and their subjects (Droid interop; tracker-sync projection) are orthogonal to a cursor review backend. No override.
- **Phase 3b.3 (strategy):** Cursor is a local-CLI review backend of the same shape as the existing `copilot`/`codex` backends — it *advances* the "Cross-model review" track and does not contradict "zero external dependencies / no SaaS" (CLI-only, no MCP/HTTP, billed to the user's own subscription). No track-rename candidates in the spec bodies.
- **Phase 4:** Downstream `.2`/`.3`/`.4` reference only canonical names that were built as specced. Line-number investigation targets point at unchanged copilot template code, not stale `.1` locations.
- **Phase 4b:** CROSS_SPEC=false → skipped.

---

Drift detected: no

Task `.1` (flowctl cursor foundation) shipped as a clean parity port; its implementation matches the spec's declared API contract exactly. No downstream task references any name, signature, or data shape that diverged.

Would update (DRY RUN): nothing — no downstream task specs require edits.

Phase 3b signals:
- Glossary renames: none (all 38 entries have empty `avoid` lists; no aliases to replace).
- Decision overrides flagged for review: none (neither active decision's module overlaps the files `.1` touched, and neither is contradicted).
- Strategy drift flagged for review: none (cursor backend aligns with the "Cross-model review" track and the local-CLI, zero-external-dependency approach).

Traceability table: parent spec's `## Requirement coverage` table is unaffected — `.1`'s R-IDs (R1–R4, R11) landed as planned; no rows change.

No files modified (DRY_RUN=true).
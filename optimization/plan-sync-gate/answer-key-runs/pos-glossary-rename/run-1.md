I have a complete picture. Let me work through the phases.

**Phase 1 — Re-anchor (fn-9.1):**
- Spec (`fn-9.1.md`) said: "Start a new **polling cycle** after each batch in `src/loop/engine.py`."
- `done_summary`: "Implemented as `run_feedback_loop` — the glossary's canonical term (the spec's 'polling cycle' is a listed avoid-alias)."
- `evidence.commits`: 506ccbae…
- Parent spec (`fn-9.md`) Approach: "fn-9.1 starts a new **polling cycle**…"

**Phase 2 — Actual implementation:**
- `src/loop/engine.py` → `def run_feedback_loop(signals):` — canonical term "feedback loop" is in the code.

**Phase 3 / 3b — Drift + glossary:**
- Husk short-circuit: `GLOSSARY_JSON.total_terms == 1` (signal present) → run **3b.1**; `DECISIONS_JSON.count == 0` → skip 3b.2; `STRATEGY_CONTENT == {}` → skip 3b.3.
- **3b.1:** entry `Feedback Loop` / avoid `["polling cycle","tick"]`. Alias "polling cycle" appears in old spec text (fn-9.1.md L3, fn-9.md L9); canonical "feedback loop" appears in new code (`run_feedback_loop`); canonical does NOT appear in old spec body → **rename confirmed in flight**. ("tick" appears nowhere.)

**Phase 4 — Downstream (fn-9.2):**
- `fn-9.2.md` L8: "Extend the **polling cycle** with exponential backoff…" → uses the stale alias → flagged.

**Phase 4b — Cross-spec:** CROSS_SPEC=false → skip.

**Phase 5 — Traceability:** `fn-9.md` has no `## Requirement coverage` table → skip. DRY_RUN=true → no edits.

---

Drift detected: yes
- fn-9.1 implemented `run_feedback_loop` (glossary canonical **Feedback Loop**); its spec + the parent spec still describe it as "polling cycle", a glossary avoid-alias. Renamed in flight.

Would update (DRY RUN):
- **fn-9.2** (`.flow/tasks/fn-9.2.md`, line 8): replace glossary alias "polling cycle" with canonical "feedback loop" → "Extend the feedback loop with exponential backoff between batches." Add breadcrumb `<!-- Updated by plan-sync: glossary rename polling cycle → Feedback Loop -->`

Would update traceability:
- None — `fn-9.md` has no `## Requirement coverage` table.

Decision overrides flagged for review:
- None — `DECISIONS_JSON.count == 0`.

Strategy drift flagged for review:
- None — `STRATEGY_CONTENT == {}` (husk).

Notes:
- "tick" alias: no occurrences in any spec/task — nothing to rename.
- Out of scope (not edited): the completed task's own spec `fn-9.1.md` and the parent spec `fn-9.md` Approach prose also contain "polling cycle", but plan-sync edits downstream task specs + the parent traceability table only (no table here), so these are left as-is.

No files modified.
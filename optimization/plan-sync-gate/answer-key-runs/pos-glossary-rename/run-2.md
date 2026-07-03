I have the complete picture. Let me work through the remaining phases.

**Phase 1 — Re-anchor (fn-9.1):** done_summary says it was implemented as `run_feedback_loop` (canonical glossary term), noting the spec's "polling cycle" is an avoid-alias. Evidence commit `506ccba` → `src/loop/engine.py`. Parent spec fn-9 R1: "Signals are re-evaluated after every batch."

**Phase 2 — Actual impl:** `src/loop/engine.py` defines `def run_feedback_loop(signals):`. Canonical term "Feedback Loop" present in code.

**Phase 3 — Drift:** completed task spec text says "polling cycle"; code shipped `run_feedback_loop`.

**Phase 3b — Husk short-circuit check:** `GLOSSARY_JSON.total_terms == 1` (signal present) → do not short-circuit. Glossary has signal → run **3b.1**, skip 3b.2 (DECISIONS count 0) and 3b.3 (STRATEGY `{}`).

**3b.1 — Glossary rename:** entry `{term: "Feedback Loop", avoid: ["polling cycle","tick"]}` (`file_count=1`, `total_terms=1` → proceed).
- Alias "polling cycle" in old spec text: fn-9.1.md L3 ✓, fn-9.md L9 ✓. ("tick" — no whole-word match anywhere.)
- Canonical term in new code: `engine.py` L1 `run_feedback_loop` ✓.
- Canonical term absent from old spec text → confirmed in-flight rename.

**Phase 4 — Downstream (fn-9.2):** L8 "Extend the polling cycle with exponential backoff between batches." references alias "polling cycle" → flag for update.

**Phase 4b:** CROSS_SPEC false → skipped.

**Phase 5 (DRY_RUN=true):** report only, no Edit. Parent spec fn-9.md has no `## Requirement coverage` table → traceability sub-step skipped. Spec prose edits are out of scope (`.flow/specs/*.md` = traceability-table-only), so fn-9.md's Approach-line alias is not an actionable edit.

---

Drift detected: yes
- fn-9.1 shipped `run_feedback_loop` (canonical glossary term "Feedback Loop") instead of the spec's "polling cycle" avoid-alias — confirmed via `src/loop/engine.py:1` against commit `506ccba`.

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`, line 8): replace glossary alias "polling cycle" with canonical "Feedback Loop" → "Extend the Feedback Loop with exponential backoff between batches." Add breadcrumb `<!-- Updated by plan-sync: glossary rename polling cycle → Feedback Loop -->`. Surrounding prose and acceptance criteria preserved; scope unchanged.

Out of scope (not edited):
- Parent spec `.flow/specs/fn-9.md` (Approach, line 9) also contains "polling cycle", but plan-sync may only edit `.flow/specs/*.md` for the `## Requirement coverage` table, which this spec has none of. Left as-is.
- Completed task `.flow/tasks/fn-9.1.md` (line 3) alias is historical (task done); not a downstream reference.

Would update traceability: none (no `## Requirement coverage` table in fn-9.md).

No decision overrides (DECISIONS_JSON count 0). No strategy drift (STRATEGY_CONTENT empty).

No files modified.
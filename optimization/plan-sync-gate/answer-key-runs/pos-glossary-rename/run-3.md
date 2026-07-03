Confirmed. The implementation (`src/loop/engine.py`) defines `run_feedback_loop` — the canonical glossary term. Now I have everything needed.

## Analysis

**Phase 1–2 (re-anchor + explore):** fn-9.1's spec said *"Start a new **polling cycle** after each batch"*; the done summary and actual code (`src/loop/engine.py`, commit `506ccba`) implemented it as `run_feedback_loop` — explicitly flagged as the glossary's canonical term over the avoid-alias.

**Phase 3 (drift):**

| Aspect | Spec Said | Actually Built |
|--------|-----------|----------------|
| Term | "polling cycle" (avoid-alias) | `run_feedback_loop` (canonical "Feedback Loop") |

**Phase 3b — husk short-circuit check:** DECISIONS_JSON.count == 0 and STRATEGY_CONTENT == {}, but GLOSSARY_JSON.total_terms == 1 → **not** a full husk. Run **3b.1 only**; skip 3b.2 and 3b.3.

**Phase 3b.1 (glossary rename):**
- Entry: term `Feedback Loop`, avoid `["polling cycle", "tick"]`.
- Alias "polling cycle" **in old spec text** → fn-9.1.md L3 ✓ and parent fn-9.md L9 ✓.
- Canonical term **in new code** → `run_feedback_loop` ✓.
- Canonical term is NOT already in old spec text → confirmed rename in flight.
- Alias "tick" → no matches anywhere. Skip.

**Phase 4 (downstream fn-9.2):** fn-9.2.md L8 — *"Extend the **polling cycle** with exponential backoff between batches."* — still references the alias. Flag for update.

**Traceability:** parent spec fn-9.md has `## Acceptance Criteria` (R1) but no `## Requirement coverage` table → skip. R1 tracks fn-9.1's re-evaluation, not fn-9.2's backoff; no `satisfies` change warranted.

DRY_RUN=true → report only, no edits.

---

Drift detected: yes
- fn-9.1 implemented the canonical glossary term `run_feedback_loop` ("Feedback Loop") instead of the spec's avoid-alias "polling cycle"

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`, L8): replace glossary alias "polling cycle" with canonical "Feedback Loop" — `"Extend the polling cycle with exponential backoff between batches."` → `"Extend the Feedback Loop with exponential backoff between batches."`; add breadcrumb `<!-- Updated by plan-sync: glossary rename polling cycle → Feedback Loop -->`

Would update traceability:
- None (no `## Requirement coverage` table in fn-9.md)

No files modified.
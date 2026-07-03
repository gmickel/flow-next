I have everything needed. Let me confirm my analysis before writing the summary.

**Phase 1–3 (drift):** `fn-9.1` spec acceptance was just "dispatch accepts a priority." Actual impl `src/pipeline/dispatch.py`: `dispatch(job, priority=0)` returns `(priority, job)` — the return **shape** changed from bare `job` to a tuple. Done summary confirms this. → Drift.

**Phase 3b:** Husk short-circuit — `GLOSSARY_JSON.total_terms == 0` AND `DECISIONS_JSON.count == 0` AND `STRATEGY_CONTENT == {}`. All three hold → entire Phase 3b skipped. No decision/strategy/glossary signals.

**Phase 4 (same-spec, fn-9.2):** fn-9.2 is a generic "document the dispatcher" task (`src/docs/notes.py`). No API name, signature, or return-shape string in its body → no stale reference to swap.

**Phase 4b (cross-spec, CROSS_SPEC=true):** Open specs = fn-9, fn-10. fn-10 (open, excluded from SPEC_ID) Approach says: *"Consume the dispatcher in `src/pipeline/dispatch.py` — the runner treats its return value as the job itself."* That is now **stale** — dispatch returns `(priority, job)`, not the bare job. No fn-10.* task specs exist; the stale reference lives in the spec prose.

**Phase 5:** No `## Requirement coverage` table in fn-9 → traceability sub-step skipped. DRY_RUN → no edits.

---

Drift detected: yes

**Completed-task drift (fn-9.1):**
- `dispatch()` return **shape** changed: now `dispatch(job, priority=0)` returns a `(priority, job)` tuple instead of the bare `job`. Confirmed in `src/pipeline/dispatch.py` and the task's own done summary ("the return SHAPE changed beyond the task wording").

**Would update — same spec (DRY RUN):**
- fn-9.2: **no edit.** Checked `.flow/tasks/fn-9.2.md` — it's a generic "document the dispatcher" task with no API/signature/return-shape reference to swap. (The doc author should capture the new `(priority, job)` tuple shape when writing the notes, but that's documentation content to author, not a stale reference for plan-sync to fix.)

**Would update — cross-spec (DRY RUN):**
- fn-10 (`.flow/specs/fn-10.md`, Approach): stale assumption *"the runner treats its return value as the job itself."* dispatch now returns `(priority, job)`, so the return value is **not** the job. Would correct the reference and add breadcrumb `<!-- Updated by plan-sync (cross-spec): fn-9.1 changed dispatch return to (priority, job) tuple -->`.
  - Caveat: fn-10 has no task specs (no `.flow/tasks/fn-10.*`), so the intended cross-spec edit target (a downstream task spec) doesn't exist — the stale reference sits in spec prose (Approach), which is outside the "traceability-table-only" spec-edit surface. Surfaced here for review rather than silently rewriting spec prose.

**Skipped:**
- Phase 3b (glossary renames / decision overrides / strategy drift): husk short-circuit — all three inputs empty.
- Traceability table update: fn-9 has no `## Requirement coverage` table.

No files modified (DRY_RUN=true).
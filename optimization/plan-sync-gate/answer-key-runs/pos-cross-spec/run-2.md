I have everything needed. Let me work through the phases.

**Phase 1 — Re-anchor (fn-9.1):** Spec said "Add priority support to `dispatch(job)`"; acceptance "dispatch accepts a priority". Done summary explicitly flags: *return SHAPE changed* — now returns `(priority, job)` tuple. Evidence commit `b3e2262`.

**Phase 2 — Actual impl:** `src/pipeline/dispatch.py`:
```python
def dispatch(job, priority=0):
    return (priority, job)
```
Confirms: signature `dispatch(job, priority=0)`, returns a `(priority, job)` tuple.

**Phase 3 — Drift:** Return shape changed from bare `job` → `(priority, job)` tuple. Real, referenced-downstream drift.

**Phase 3b — Skipped (husk short-circuit):** `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` — all three hold. No project-anchor signal.

**Phase 4 — Downstream (fn-9.2):** Pure docs task ("Document the dispatcher", `src/docs/notes.py`). No stale reference — it asserts nothing about return shape. Nothing to edit.

**Phase 4b — Cross-spec (enabled):** Open specs excluding fn-9 → fn-10 (open). fn-10 Approach: *"the runner treats its return value as the job itself"* — directly contradicts the new tuple return. Clear cross-spec stale integration-point reference.

**Phase 5 — DRY_RUN, report only.** No `## Requirement coverage` table in fn-9 → traceability skipped.

---

Drift detected: yes
- fn-9.1 changed the return SHAPE of `dispatch()` — returns `(priority, job)` tuple, not the bare job (signature now `dispatch(job, priority=0)`).

Would update (DRY RUN) — cross-spec:
- **fn-10** (`.flow/specs/fn-10.md`, Approach): stale assumption "the runner treats its return value as the job itself" → `dispatch()` now returns `(priority, job)`, so the job is `dispatch(...)[1]`. Would rewrite the Approach line to reflect the tuple return + add breadcrumb `<!-- Updated by plan-sync (cross-spec): fn-9.1 changed dispatch return to (priority, job) tuple -->`.

Same-spec downstream:
- **fn-9.2**: no stale reference (docs task, no return-shape assumption) — no change. Note for whoever implements it: docs should describe the `(priority, job)` tuple return.

Not run / not applicable:
- Phase 3b (glossary / decision / strategy): skipped — husk short-circuit (all three signals empty).
- Traceability table: none in fn-9 → skipped.

No files modified (DRY_RUN=true).
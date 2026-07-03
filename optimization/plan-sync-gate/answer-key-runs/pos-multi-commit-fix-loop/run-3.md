Analysis complete. Confirmed drift.

**Phase 1 (re-anchor):** fn-9.1 spec called for `compute_total(lines)` in `src/billing/calc.py`. Done summary + commit `bbfa1af` say it shipped as `compute_grand_total(lines, tax=0)`.

**Phase 2 (actual impl):** `src/billing/calc.py:1` → `def compute_grand_total(lines, tax=0):`. Confirmed.

**Phase 3 (drift):**

| Aspect | Spec Said | Actually Built |
|--------|-----------|----------------|
| Fn name | `compute_total` | `compute_grand_total` |
| Signature | `(lines)` | `(lines, tax=0)` |

**Phase 3b:** Husk short-circuit — `total_terms == 0`, `count == 0`, `STRATEGY_CONTENT == {}`. All three hold → skipped entirely.

**Phase 4 (downstream):** fn-9.2 (`.flow/tasks/fn-9.2.md:8`) references stale `compute_total`. Needs update.

**Phase 4b:** CROSS_SPEC false → skipped.

**Phase 5:** DRY_RUN true → no edits. Parent spec `fn-9.md` has no `## Requirement coverage` table → traceability sub-step skipped.

---

Drift detected: yes
- fn-9.1 shipped `compute_grand_total(lines, tax=0)` instead of the planned `compute_total(lines)` (renamed in flight, added optional `tax` param)

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md:8`): change reference `compute_total` → `compute_grand_total`; append breadcrumb `<!-- Updated by plan-sync: fn-9.1 used compute_grand_total not compute_total -->`

No traceability table in `fn-9.md` → no traceability changes.

No decision overrides flagged (husk).

No strategy drift flagged (husk).

No files modified (DRY_RUN).
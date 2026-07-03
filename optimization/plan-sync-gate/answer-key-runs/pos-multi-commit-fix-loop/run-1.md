All phases complete. Here is my **Phase 6 summary**.

Drift detected: yes
- fn-9.1 renamed `compute_total(lines)` → `compute_grand_total(lines, tax=0)` in `src/billing/calc.py` (added `tax=0` param, verified in code).

Would update (DRY RUN):
- **fn-9.2** (`.flow/tasks/fn-9.2.md`, line 8): change the stale reference `Sum via `compute_total`` → `Sum via `compute_grand_total``. Default `tax=0` means an unmodified `compute_grand_total(lines)` call still sums correctly, so only the name is stale. Add breadcrumb: `<!-- Updated by plan-sync: fn-9.1 used compute_grand_total not compute_total -->`.

Notes:
- Phase 3b skipped entirely (husk short-circuit): `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, and `STRATEGY_CONTENT == {}` — no project-anchor signal. No decision overrides or strategy drift to surface.
- Phase 4b skipped (CROSS_SPEC = false).
- Traceability: parent spec `.flow/specs/fn-9.md` has no `## Requirement coverage` table — sub-step skipped. R1 unaffected.

No files modified.
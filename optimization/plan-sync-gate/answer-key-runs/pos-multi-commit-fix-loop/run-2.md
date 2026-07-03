Everything needed is confirmed. Here's my Phase 6 summary.

---

Drift detected: yes
- fn-9.1 renamed `compute_total(lines)` → `compute_grand_total(lines, tax=0)` (added optional `tax=0` param + tax support). Verified against working tree: `src/billing/calc.py` defines `compute_grand_total(lines, tax=0)`. The done summary records the rename; evidence commit `bbfa1af` is the r2 review-notes commit ("review rounds 1-2 only touched notes"), so the rename actually landed in the earlier feature commit (`d1605c9 feat(billing): grand total`) — the code confirms it either way.

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`, line 8): change `Sum via \`compute_total\`` → `Sum via \`compute_grand_total\``; add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used compute_grand_total not compute_total -->`. The new `tax=0` param is optional, so a lines-only call stays valid — name is the only stale reference.

Phase 3b (glossary / decisions / strategy): skipped — husk short-circuit (all of `total_terms == 0`, `count == 0`, `STRATEGY_CONTENT == {}`).
Phase 4b (cross-spec): skipped — CROSS_SPEC is false.
Traceability: no `## Requirement coverage` table in `.flow/specs/fn-9.md` — nothing to update.

No files modified.
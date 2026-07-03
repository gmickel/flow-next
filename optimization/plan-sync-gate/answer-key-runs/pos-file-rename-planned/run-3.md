I have a complete picture. Let me verify my findings before writing the summary.

**Phase 1 — Completed task (fn-9.1):** Move `src/mod/alpha.py` → `src/core/alpha_core.py`, mechanical, no content changes. Done summary: "Moved exactly as planned." Evidence commit `d30375b`.

**Phase 2 — Actual implementation:** `src/core/alpha_core.py` exists (`def entry(): return 1`); `src/mod/alpha.py` no longer exists. Move landed exactly as planned.

**Phase 3 — Drift:** The module's file path changed. fn-9.2's `**Files:**` line still points at the pre-relocation path `src/mod/alpha.py` (its own body admits it was "written before the relocation landed").

**Phase 3b — Husk short-circuit:** `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` → all three hold. Entire Phase 3b skipped.

**Phase 4 — Downstream (fn-9.2):** references stale path `src/mod/alpha.py`. Task intent (add a second entry point) preserved; only the path is stale.

**Phase 4b — Cross-spec:** CROSS_SPEC false → skipped.

**Phase 5 (DRY_RUN=true):** report only. Parent spec `fn-9.md` has no `## Requirement coverage` table → traceability sub-step skipped. No R-ID renumbering; drift is a path correction, not a coverage change, so no `satisfies` edit.

---

Drift detected: yes
- fn-9.1 relocated the alpha module from `src/mod/alpha.py` to `src/core/alpha_core.py` (mechanical move, no content change; confirmed `src/mod/alpha.py` is gone, `src/core/alpha_core.py` holds `entry()`)

Would update (DRY RUN):
- fn-9.2: Change the `**Files:**` path `src/mod/alpha.py` → `src/core/alpha_core.py` (module relocated by fn-9.1). Add breadcrumb `<!-- Updated by plan-sync: fn-9.1 relocated module to src/core/alpha_core.py not src/mod/alpha.py -->`. The task's own note ("written before the relocation landed") is left as-is — it's prose, not a stale path, and scope/acceptance are unchanged.

No traceability table in `fn-9.md` → no traceability changes.
No glossary / decision / strategy signal (husk short-circuit) → nothing flagged.

No files modified.
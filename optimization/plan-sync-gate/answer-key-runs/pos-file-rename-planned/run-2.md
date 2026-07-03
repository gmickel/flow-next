## Analysis complete

**Phase 1 — Completed task (fn-9.1):** Relocate `src/mod/alpha.py` → `src/core/alpha_core.py`, mechanical move, no content changes. Done summary: "Moved exactly as planned; no content changes." Evidence commit `d30375b`.

**Phase 2 — Actual implementation:** Confirmed. `src/mod/alpha.py` and the entire `src/mod/` dir are gone; `src/core/alpha_core.py` exists with `def entry(): return 1`. Move landed exactly as spec'd — no naming/API/signature drift in the code itself.

**Phase 3 — Drift:** The relocation is real. Old path `src/mod/alpha.py` now survives only in flow files. Two of those are correct historical records (fn-9.1 task = what was moved; fn-9 spec Approach = describes the move). The third — downstream **fn-9.2** — still lists `**Files:** src/mod/alpha.py` as its target, a path that no longer exists. fn-9.2's own note ("written before the relocation landed") confirms this is stale, not intentional.

**Phase 3b — skipped** (husk short-circuit: `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}`).

**Phase 4 — Downstream (fn-9.2):** Stale file path is the only drift. Acceptance ("second entry point available") is a requirement, not a stale reference — left untouched.

**Phase 4b — skipped** (CROSS_SPEC false).

**Phase 5 — DRY_RUN true:** report only. No `## Requirement coverage` table in fn-9 → no traceability changes. fn-9.2 is an extension task; its drift doesn't advance R1 ("Alpha module lives under src/core/", satisfied by fn-9.1) → no `satisfies` change.

---

Drift detected: yes
- fn-9.1 relocated the module to `src/core/alpha_core.py`; downstream fn-9.2 still targets the pre-move path `src/mod/alpha.py`, which no longer exists.

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`, line 6): Change `**Files:** ` + "`src/mod/alpha.py`" → `**Files:** ` + "`src/core/alpha_core.py`"; add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used src/core/alpha_core.py not src/mod/alpha.py -->`

Would update traceability: none (no `## Requirement coverage` table in fn-9).

Left unchanged (accurate historical records): `.flow/tasks/fn-9.1.md` and `.flow/specs/fn-9.md` — both correctly describe the `src/mod/alpha.py` → `src/core/alpha_core.py` move.

No files modified.
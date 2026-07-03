I've completed my investigation across all phases. Here's what I found before the summary:

- **Phase 2 (actual impl):** Helpers now live at `src/common/strings.py` (`slug`) and `src/common/dates.py` (`today`). `src/util/` is gone entirely. `src/app/main.py` currently has no imports (`def run(): return 0`). Evidence commit `1091b7c` matches git log.
- **Phase 3 (drift):** fn-9.1 matched its own spec exactly (mechanical move, no content change). But the relocation `src/util/` → `src/common/` is an integration point that downstream fn-9.2 references with the now-dead path.
- **Phase 3b:** Husk short-circuit — `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, and `STRATEGY_CONTENT == {}`. All three hold → entire Phase 3b skipped (no glossary/decision/strategy signal).
- **Phase 4 (downstream):** fn-9.2 says "Import the helpers from `src/util/`" and is explicitly annotated "(written before the consolidation landed)." That path no longer exists; importing from it fails fn-9.2's own acceptance ("app imports resolve"). Stale reference → needs `src/common/`. Its Files list (`src/app/main.py`) and acceptance are correct.
- **Phase 4b:** CROSS_SPEC false → skipped.
- **Phase 5:** Parent spec `fn-9.md` is already consistent (Overview + Approach + R1 all reference `src/common/` correctly, Approach accurately narrates the move *from* `src/util/`) — no parent-spec edit. No `## Requirement coverage` table exists → traceability sub-step skipped. R1 already satisfied by fn-9.1; no R-ID changes.

---

Drift detected: yes
- fn-9.1 relocated the helper modules to `src/common/` (`src/common/strings.py`, `src/common/dates.py`) and removed `src/util/` — exactly as its own spec planned. Downstream fn-9.2 still references the pre-move import path `src/util/`, which no longer exists.

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`): change the import source from ``Import the helpers from `src/util/` into the app entrypoint`` → ``Import the helpers from `src/common/` into the app entrypoint``; add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used src/common/ not src/util/ -->`. Files list (`src/app/main.py`) and the acceptance criterion left unchanged.

No files modified.
Confirmed the drift. Line 1 of `src/config/loader.py` ships `max_retries`, not the planned `retry_max`.

**Phase 3 — Drift table:**

| Aspect | Spec Said | Actually Built |
|--------|-----------|----------------|
| Config key | `retry_max` | `max_retries` |

**Phase 3b:** Husk short-circuit applies — `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}`. All three hold → entire Phase 3b skipped.

**Phase 4 — Downstream check:** `fn-9.2` (`.flow/tasks/fn-9.2.md:11`) documents `mytool set retry_max=5` — the stale key. The done summary explicitly warns this class of setup command is now a no-op against shipped code.

**Phase 4b:** `CROSS_SPEC` is false → skipped.

**Phase 5:** `DRY_RUN` is true → report only. Parent spec `fn-9.md` has no `## Requirement coverage` table → traceability sub-step skipped. (Spec prose `fn-9.md:9` also names `retry_max`, but spec edits are restricted to the traceability table, and that line describes the completed task's own plan — out of scope.)

---

Drift detected: yes
- fn-9.1 shipped config key `max_retries` instead of the planned `retry_max` (confirmed in `src/config/loader.py:1`: `DEFAULTS = {"max_retries": 3}`)

Would update (DRY RUN):
- fn-9.2: Change documented setup command `mytool set retry_max=5` → `mytool set max_retries=5`; add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used max_retries not retry_max -->`

No files modified.
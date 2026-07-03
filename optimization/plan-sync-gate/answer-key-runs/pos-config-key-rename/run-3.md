Confirmed. The actual code at `src/config/loader.py:1` is `DEFAULTS = {"max_retries": 3}` — the key shipped as `max_retries`, not the planned `retry_max`.

Phase analysis complete:
- **Phase 1–3:** Drift confirmed. fn-9.1 spec/task planned `retry_max`; implementation shipped `max_retries`.
- **Phase 3b:** Husk short-circuit — `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` all hold → entire Phase 3b skipped (no glossary/decision/strategy signal).
- **Phase 4:** fn-9.2 references the stale key at `.flow/tasks/fn-9.2.md:11` (`mytool set retry_max=5`) — the very setup command it exists to document. Per the done summary, that command is now a no-op.
- **Phase 4b:** `CROSS_SPEC` is false → skipped.
- **Traceability:** parent spec `fn-9.md` has no `## Requirement coverage` table → skipped.

---

Drift detected: yes
- fn-9.1 shipped config key `max_retries` instead of the planned `retry_max` (house naming); the spec ceiling landed as `DEFAULTS = {"max_retries": 3}` in `src/config/loader.py`, and setup commands using the old key are no-ops.

Would update (DRY RUN):
- **fn-9.2** (`.flow/tasks/fn-9.2.md:11`): change the documented setup command `mytool set retry_max=5` → `mytool set max_retries=5`, with breadcrumb `<!-- Updated by plan-sync: fn-9.1 used max_retries not retry_max -->`. This is the only stale reference in a downstream task; fn-9.2's purpose is to document the retry setup command, so the key must match the shipped name or the docs would instruct a no-op.

Not updated (out of scope):
- Parent spec `.flow/specs/fn-9.md:9` Approach line still reads "fn-9.1 ships the retry_max setting" — stale, but spec edits are restricted to the traceability table (none exists here), and it is a historical note about the completed task, not a downstream reference. Flagged for awareness only.
- fn-9.1's own description (`.flow/tasks/fn-9.1.md:3`) — completed task, already reconciled by its done summary.

Would update traceability: none (no `## Requirement coverage` table in fn-9.md).

No glossary renames, decision overrides, or strategy drift (Phase 3b short-circuited — no project-anchor signal).

No files modified.
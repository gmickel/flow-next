Everything confirmed. The only stale downstream reference is fn-9.2 line 8. The parent spec fn-9.md has no `## Requirement coverage` table, so the traceability sub-step is skipped. Phase 3b is husk-short-circuited; Phase 4b is skipped (CROSS_SPEC false). DRY_RUN is true, so no edits — here is the Phase 6 summary.

---

Drift detected: yes
- fn-9.1 shipped the line helper as `read` in `src/reader.py`, not `parse` as the task spec specified (renamed in flight to match the sibling io module naming).

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`, line 8): change "Feed each line through the **parse** helper before adding it as a row." → "Feed each line through the **read** helper …", with breadcrumb `<!-- Updated by plan-sync: fn-9.1 used read not parse -->`. This is the only stale reference — the downstream task assumes a helper named `parse` that does not exist.

Would update traceability:
- N/A — parent spec `fn-9.md` has no `## Requirement coverage` table.

Notes:
- Phase 3b skipped (husk short-circuit): glossary `total_terms == 0`, decisions `count == 0`, strategy `{}` — no project-anchor signal.
- Phase 4b skipped (CROSS_SPEC = false).
- Parent spec approach text references the tasks by id only, not the helper name, so no edit needed there.
- No decision overrides flagged. No strategy drift flagged.

No files modified.
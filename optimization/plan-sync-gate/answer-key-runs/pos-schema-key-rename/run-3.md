I have everything I need. Let me work through the phases.

**Phase 1 — Re-anchor on completed task (fn-9.1):**
- Spec/description said: serialize with a `user_id` key in `src/api/serialize.py`.
- `done_summary`: "Shipped the wire key as `uid` instead of `user_id` (payload-size review) — the wire schema differs from the spec."
- Evidence commit: `6a583f2`.

**Phase 2 — Actual implementation:** `src/api/serialize.py` →
```python
def to_wire(user):
    return {"uid": user["id"], "name": user["name"]}
```
Confirmed: wire key is `uid`, not `user_id`.

**Phase 3 — Drift:**

| Aspect | Spec said | Actually built |
|--------|-----------|----------------|
| Wire key | `user_id` | `uid` |

**Phase 3b —** Husk short-circuit: `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` — all three hold. Entire Phase 3b skipped (no anchor signal).

**Phase 4 — Downstream (fn-9.2):** Its "Expected payload" JSON block hardcodes `{"user_id": 7, "name": "ada"}` — stale. The wire dict now emits `uid`, so an SDK built to read `user_id` would break R1 (round-trip). Flagged.

**Phase 4b —** CROSS_SPEC is "false" — skipped.

**Phase 5 —** DRY_RUN "true": report only, no edits. Parent spec `fn-9.md` has no `## Requirement coverage` table — traceability sub-step skipped. No `satisfies` change warranted (key rename doesn't change which R-IDs fn-9.2 covers).

---

Drift detected: yes
- fn-9.1 shipped wire key `uid` instead of the spec's `user_id` (`src/api/serialize.py` → `to_wire()` returns `{"uid": user["id"], ...}`; recorded in its done summary, evidence `6a583f2`)

Would update (DRY RUN):
- **fn-9.2** (`.flow/tasks/fn-9.2.md`): in the "Expected payload" JSON block, change key `user_id` → `uid` (`{"user_id": 7, "name": "ada"}` → `{"uid": 7, "name": "ada"}`); add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used uid not user_id -->`. The generic acceptance line ("SDK reads the id from the wire dict") is unaffected — left as-is.

Would update traceability:
- None — `fn-9.md` has no `## Requirement coverage` table.

Phase 3b (glossary / decisions / strategy): skipped — all three husk (no signal).

No files modified.
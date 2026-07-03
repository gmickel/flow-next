I now have everything needed. Let me analyze the drift.

## Analysis

**Phase 1 — Completed task (fn-9.1)**
- Spec: "Harden `fetch_user(user_id)` in `src/api/users.py` (validation only, **keep the signature**)."
- done_summary: added a **required** keyword-only `scope` parameter (explicitly "beyond the task's keep-the-signature instruction").
- Evidence commit `fddf896` = "feat(api): scoped user fetch (fn-9.1)" ✓ consistent.

**Phase 2 — Actual implementation** (`src/api/users.py`):
```python
def fetch_user(user_id, *, scope):
    return {"id": user_id, "scope": scope}
```

**Phase 3 — Drift**

| Aspect | Spec said | Actually built |
|--------|-----------|----------------|
| Signature | `fetch_user(user_id)` (keep the signature) | `fetch_user(user_id, *, scope)` — `scope` required, keyword-only |

Real, downstream-relevant drift: the call shape changed and `scope` is now mandatory.

**Phase 3b — Husk short-circuit:** `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` — all three hold. Entire Phase 3b skipped (no project-anchor signal).

**Phase 4 — Downstream (fn-9.2):** "Route handler delegates to the user fetch API"; Investigation target `src/api/users.py:1-30` ("call shape to preserve"). The integration point it delegates to changed — a bare `fetch_user(user_id)` now raises `TypeError` because `scope` is required. fn-9.2 needs the updated call shape. Flagged.

**Phase 4b — Cross-spec:** CROSS_SPEC false → skipped.

**Phase 5 — Traceability:** `.flow/specs/fn-9.md` has an `## Acceptance Criteria` section (R1 only) but **no `## Requirement coverage` table** → traceability sub-step skipped. DRY_RUN true → no edits.

---

Drift detected: yes
- fn-9.1 changed the call shape: implemented `fetch_user(user_id, *, scope)` with a REQUIRED keyword-only `scope`, instead of the spec's `fetch_user(user_id)` ("keep the signature"). Callers must now pass `scope` explicitly.

Would update (DRY RUN):
- fn-9.2 (`.flow/tasks/fn-9.2.md`): Update the delegation/"call shape to preserve" reference to reflect the new signature — the route handler must call `fetch_user(user_id, scope=<...>)`; a bare `fetch_user(user_id)` will raise `TypeError`. Add breadcrumb: `<!-- Updated by plan-sync: fn-9.1 used fetch_user(user_id, *, scope) not fetch_user(user_id) -->`

Would update traceability: none (no `## Requirement coverage` table in fn-9.md).

Decision overrides flagged for review: none (no decision entries).

Strategy drift flagged for review: none (no STRATEGY.md signal).

No files modified.
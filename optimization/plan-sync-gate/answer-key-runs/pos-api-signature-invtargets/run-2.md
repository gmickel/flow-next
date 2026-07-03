I have everything needed. Let me work through the phases.

**Phase 1 — Re-anchor (fn-9.1):** Spec said harden `fetch_user(user_id)` — *validation only, keep the signature*. Done summary admits it added a **required keyword-only `scope`** parameter. Evidence commit `fddf896`.

**Phase 2 — Actual implementation** (`src/api/users.py`):
```python
def fetch_user(user_id, *, scope):
    return {"id": user_id, "scope": scope}
```
Confirms drift: signature is now `fetch_user(user_id, *, scope)` — `scope` is mandatory.

**Phase 3 — Drift:**

| Aspect | Spec said | Actually built |
|--------|-----------|----------------|
| Signature | `fetch_user(user_id)` (keep) | `fetch_user(user_id, *, scope)` — required kw-only `scope` |

**Phase 3b — Husk short-circuit:** `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, `STRATEGY_CONTENT == {}` — all three hold → entire Phase 3b skipped (no glossary/decision/strategy signal).

**Phase 4 — Downstream (fn-9.2):** Task "delegates to the user fetch API"; its Required investigation target is `src/api/users.py:1-30` ("call shape to preserve"); `depends_on: fn-9.1`. That call shape is exactly the integration point that drifted — fn-9.2's handler must now supply a `scope` argument it currently has no plan for.

**Phase 4b:** CROSS_SPEC false → skipped.
**Traceability:** fn-9 spec has `## Acceptance Criteria` (R1) but no `## Requirement coverage` table → sub-step skipped. R1 still maps to fn-9.2; no R-ID/`satisfies` changes warranted.

**Phase 5:** DRY_RUN true → report only, no edits.

---

Drift detected: yes
- fn-9.1 added a **required keyword-only `scope`** parameter while hardening, contradicting the spec's "keep the signature" instruction. Actual signature: `fetch_user(user_id, *, scope)`; returns `{"id": user_id, "scope": scope}`.

Would update (DRY RUN):
- **fn-9.2**: Flag that the user fetch API is no longer callable as `fetch_user(user_id)` — the route handler must pass `scope` explicitly, e.g. `fetch_user(user_id, scope=...)`. Annotate the "call shape to preserve" investigation target accordingly and add breadcrumb `<!-- Updated by plan-sync: fn-9.1 used fetch_user(user_id, *, scope) not fetch_user(user_id) -->`.

Would update traceability: none (fn-9 spec has no `## Requirement coverage` table).

No decision overrides / strategy drift (husk short-circuit — glossary, decisions, and strategy all empty).

No files modified.
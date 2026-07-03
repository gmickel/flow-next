## Analysis

**Phase 1 — Completed task (fn-9.1):** Spec instruction was *"Harden `fetch_user(user_id)` … (validation only, **keep the signature**)."* The done summary self-reports a deviation: *"Added a REQUIRED keyword-only `scope` parameter … beyond the task's keep-the-signature instruction."* Evidence commit `fddf896`.

**Phase 2 — Actual code** (`src/api/users.py`):
```python
def fetch_user(user_id, *, scope):
    return {"id": user_id, "scope": scope}
```
Confirms the signature changed — `scope` is now a required keyword-only argument.

**Phase 3 — Drift:**

| Aspect | Spec said | Actually built |
|--------|-----------|----------------|
| Signature | `fetch_user(user_id)` (keep it) | `fetch_user(user_id, *, scope)` |
| Call shape | `fetch_user(user_id)` | `fetch_user(user_id, scope=...)` — `scope` mandatory |

**Phase 3b — Husk short-circuit:** `GLOSSARY_JSON.total_terms == 0`, `DECISIONS_JSON.count == 0`, and `STRATEGY_CONTENT == {}` — all three hold. Skipped entirely (no glossary/decision/strategy signal).

**Phase 4 — Downstream (fn-9.2):** Mounts the web route; *"Route handler delegates to the user fetch API,"* with required investigation target `src/api/users.py:1-30` annotated *"(call shape to preserve)."* That call shape is exactly what drifted — fn-9.2's handler must now pass `scope=`, and the "preserve" annotation is stale. `src/web/routes.py` is still an empty `ROUTES = []`, so no code has hardcoded the old shape yet, but the task spec's stated call contract is wrong.

**Phase 4b:** `CROSS_SPEC` false — skipped.

**Phase 5 — Traceability:** fn-9.md has `## Acceptance Criteria` (R1) but no `## Requirement coverage` table — sub-step skipped. DRY_RUN → no edits.

---

Drift detected: yes
- fn-9.1 added a REQUIRED keyword-only `scope` to `fetch_user` (signature now `fetch_user(user_id, *, scope)`), contradicting its "keep the signature" instruction. Callers must now pass `scope=` explicitly.

Would update (DRY RUN):
- fn-9.2: Correct the delegation call shape from `fetch_user(user_id)` to `fetch_user(user_id, scope=...)` — the required keyword-only `scope` must be supplied by the route handler.
- fn-9.2: The investigation-target annotation `src/api/users.py:1-30` *"(call shape to preserve)"* is now stale; the call shape changed. Would reword to point at the actual `fetch_user(user_id, *, scope)` signature.
- Breadcrumb that would be added to `.flow/tasks/fn-9.2.md`: `<!-- Updated by plan-sync: fn-9.1 used fetch_user(user_id, *, scope) not fetch_user(user_id) -->`

No traceability table in fn-9 — traceability update skipped.
No decision overrides (DECISIONS_JSON husk).
No strategy drift (STRATEGY_CONTENT husk).

No files modified (DRY_RUN=true).
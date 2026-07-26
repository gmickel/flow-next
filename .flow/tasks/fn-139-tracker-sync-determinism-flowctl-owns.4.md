---
satisfies: [R5, R6, R10, R25, R31]
---
# fn-139-tracker-sync-determinism-flowctl-owns.4 Capabilities: attachments, relations, tier detection, degradation

## Description
Implement capability-gated verbs and the `capabilities` descriptor.

Attachments (R10): Jira needs `X-Atlassian-Token: no-check` (omitting it returns **404**, not 403); Linear is two-step presigned PUT with declared size matching exactly; GitLab retrieval works ONLY via `GET /projects/:id/uploads/:upload_id` (the markdown `/uploads/<secret>/` path needs a session cookie); GitHub has **no attachment API** so `capabilities.attachments` is false and the commit-and-link workaround documents the expiring-token caveat for private repos.

Relations (R25): reproduce fn-64's full contract - `depRelations` provenance ledger, additive-only, completed-blocker rule, never-clobber-on-collision (defer + queue), and `<!-- flow:deps -->` exclusion from body-merge divergence hashing. GitLab `is_blocked_by` is tier-gated: detect via `GET /namespaces/:id -> plan`, degrade to `relates_to` on Free with a structured `degraded` field.

## Acceptance
- [ ] Attachment upload AND byte-identical retrieval asserted per adapter (fake transport)
- [ ] Jira attach without the XSRF header is handled as auth-shape, not "endpoint missing"
- [ ] GitLab retrieval uses upload_id, not the markdown path
- [ ] GitHub records attachments:false; workaround documents the expiring-token caveat
- [ ] `relate` reproduces ledger + additive-only + completed-blocker + never-clobber
- [ ] Free tier degrades to relates_to with a structured `degraded` field, not prose
- [ ] `<!-- flow:deps -->` excluded from divergence hashing

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

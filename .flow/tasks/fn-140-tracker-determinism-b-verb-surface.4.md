---
satisfies: [R9, R10, R11, R15]
---
# fn-140-tracker-determinism-b-verb-surface.4 Capabilities: attachments, relations, tier degradation

## Description
Implement capability-gated verbs and resolve every capability asymmetry (R15) rather than leaving contracts undecided.

Attachments, each via its own measured route: Jira needs `X-Atlassian-Token: no-check` (omitting it returns **404**, not 403); Linear is two-step presigned PUT with declared size matching exactly, retrieval needs the auth header; GitLab retrieval works ONLY via `GET /projects/:id/uploads/:upload_id` (the markdown `/uploads/<secret>/` path needs a session cookie); GitHub has no API so `attachments: false`.

Relations reproduce **fn-64's full contract**: `depRelations` ledger, additive-only, completed-blocker rule, never-clobber-on-collision (defer + queue), `<!-- flow:deps -->` excluded from divergence hashing. GitLab degrades to `relates_to` on Free via the resolved `plan`.

Decide and implement: `deleteIssue` verb-or-dropped; `subIssues` consumer-or-dropped; Linear unknown-label behavior; repeated `--add` on single-assignee trackers.

## Acceptance
- [ ] Upload AND byte-identical retrieval asserted per adapter
- [ ] Jira attach without XSRF header handled as auth-shape, not "endpoint missing"
- [ ] GitLab retrieval uses upload_id, not the markdown path
- [ ] `relate` reproduces ledger + additive-only + completed-blocker + never-clobber
- [ ] Free tier degrades to relates_to via structured `degraded` field
- [ ] Every R15 asymmetry decided and implemented; no test targets an undecided contract

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R9, R10, R11, R15]
---
# fn-140-tracker-determinism-b-verb-surface.4 Capabilities: attachments, relations, tier degradation

## Description
Implement capability-gated verbs and resolve every capability asymmetry (R15) rather than leaving contracts undecided.

**Credential policy is load-bearing here**: Linear's presigned `PUT` must carry `presigned-anonymous` (no Linear key - it targets a third-party asset host), while its asset **retrieval** carries auth. GitLab uploads use the **HTTP/multipart route**, never `glab api -F file=@` (invalid multipart, measured). Both are spec A R4b.

Attachments, each via its own measured route: Jira needs `X-Atlassian-Token: no-check` (omitting it returns **404**, not 403); Linear is two-step presigned PUT with declared size matching exactly, retrieval needs the auth header; GitLab retrieval works ONLY via `GET /projects/:id/uploads/:upload_id` (the markdown `/uploads/<secret>/` path needs a session cookie); GitHub has no API so `attachments: false`.

Relations reproduce **fn-64's full contract**: `depRelations` ledger, additive-only, completed-blocker rule, never-clobber-on-collision (defer + queue), `<!-- flow:deps -->` excluded from divergence hashing. GitLab degrades to `relates_to` on Free via the resolved `plan`.

The capability table is decided in spec A - implement it, do not re-open it. Consumers: `deleteIssue` gates cleanup paths; `subIssues` is dependency projection's **degraded GitHub form** and is hierarchy, **never** presented as blocked-by. Unknown Linear label -> **auto-create** (matches GitHub/GitLab create-on-demand). Repeated `--add` on a single-assignee tracker -> **replace**, reported in `degraded`.

## Acceptance
- [ ] Upload AND byte-identical retrieval asserted per adapter
- [ ] Linear presigned PUT carries NO provider credential; retrieval does (asserted)
- [ ] GitLab upload uses HTTP/multipart, never `glab api -F`
- [ ] Jira attach without XSRF header handled as auth-shape, not "endpoint missing"
- [ ] GitLab retrieval uses upload_id, not the markdown path
- [ ] `relate` reproduces ledger + additive-only + completed-blocker(-still-projects) + never-clobber (the `<!-- flow:deps -->` HASH-EXCLUSION half of R10 completes in .5 where body-divergence hashing exists; marker constants ship here)
- [ ] Free tier degrades to relates_to via structured `degraded` field
- [ ] Capability table implemented per spec A; not re-litigated
- [ ] GitHub sub-issues never surfaced as a blocking relation
- [ ] Unknown Linear label auto-created; single-assignee repeated `--add` replaces + reports

## Done summary
Attachments + relations + capability asymmetries shipped (grok-4.5 implementation, host + codex hardening over 3 rounds).

attach/: wire attach / attach-get on the measured routes (jira multipart + XSRF header with the 404 surfaced as xsrf; linear two-step presigned PUT carrying PRESIGNED_ANONYMOUS with exact size then attachmentCreate success-required, retrieval restricted to trusted https linear asset hosts - the arbitrary-URL credential-exfiltration primitive is closed and pinned; gitlab HTTP multipart + upload_id retrieval; github gated class capability pre-request). Random payload-collision-checked multipart boundary. Upload/download both return sha256 for byte-identity assertions.

relate/: fn-64 contract with the 4-way ledger x remote classification BEFORE mutation (probe-only provider reads): ledger+remote noop, ledger+missing = human-removal collision QUEUED (default not re-created), unledgered+remote = foreign-edge collision QUEUED (canonical deferred-decisions sink + status=queued receipts), neither = create. Completed blockers PROJECT (visible historical ordering; readiness alone excludes them) - the reviewer caught the inverted port. Ledger persistence serialized under the shared .flow writer lock (barrier-race pinned). Edge keys byte-identical to flowctl. GitHub sub_issues = hierarchy proxy only, never blocked-by. GitLab is_blocked_by / relates_to degrade with structured degraded. Jira directional Blocks (probe signature bug fixed + coverage added).

R15 asymmetries: unknown Linear label auto-creates; single-assignee repeated --add replaces + reports in degraded. flow:deps hash exclusion completes in .5 (annotated; marker constants ship here).

3 codex rounds: 8 -> 2 -> SHIP.
## Evidence
- Commits: 638fcddc, 2c42683d, 7e175b27
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_capabilities -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs:
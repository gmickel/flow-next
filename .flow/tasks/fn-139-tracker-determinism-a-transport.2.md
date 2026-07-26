---
satisfies: [R4,R5,R6,R7,R14]
---

# fn-139-tracker-determinism-a-transport.2 Injected executor: Request/Response types, bounds, classification
# fn-139-tracker-sync-determinism-flowctl-owns.2 Wire verbs: read/update/comment CRUD/label/assign + persist-external

## Description
Build the transport seam every adapter calls. Specified, not aspirational:

`Request{method,url_or_argv,headers,body,timeout_s,idempotent}` / `Response{status,headers,body,elapsed_s}`, with GraphQL errors arriving over HTTP 200/400 normalized here rather than in each adapter.

Bounds: connect 5s / read 30s; max 2 retries on `rate_limited` only, exponential backoff capped 30s; concurrency cap 4. Credential precedence env -> Keychain -> CLI config -> unauthenticated, with redaction at the executor boundary.

**Classification is per-adapter and tabulated.** `401/403 = auth` is insufficient: GitLab returns 403 for both a bad token and a licence-gated `is_blocked_by`, and Linear rate limiting arrives as a GraphQL error over HTTP 400.

Result envelope, exhaustive class enum, fixed numeric exit codes. JSON on stdout, human notes on stderr.

## Acceptance
- [ ] Request/Response types implemented; GraphQL-over-200/400 normalized in the executor
- [ ] Per-adapter classification table: GitLab 403+licence-body -> capability, bare 403 -> auth; Linear GraphQL 400 -> rate_limited
- [ ] Bounds enforced and asserted (timeout, 2 retries, backoff clamp, concurrency 4)
- [ ] Credential precedence + redaction at the boundary; no token in any log/receipt/error (test)
- [ ] Content-bearing args never in argv (body with shell metacharacters)
- [ ] Envelope + class enum + numeric exit codes; JSON stdout, notes stderr

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

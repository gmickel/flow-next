---
satisfies: [R4,R5,R6,R7,R14]
---

# fn-139-tracker-determinism-a-transport.2 Injected executor: Request/Response types, bounds, classification
# fn-139-tracker-sync-determinism-flowctl-owns.2 Wire verbs: read/update/comment CRUD/label/assign + persist-external

## Description
Build the transport seam every adapter calls. Specified, not aspirational:

Use the epic's schema verbatim - `Request{provider, op, method, url_or_argv, headers (NEVER authorization), body, timeout_s, idempotent}` and `Response{status, headers, body, elapsed_s}`. A **single** `timeout_s`: separate connect/read deadlines are not achievable with the chosen transports.

Executor signature returns `Response | TrackerError` - never raises a transport-native exception upward. GraphQL errors arriving over HTTP 200/400 are normalized in the executor, not in each adapter.

Bounds: **one `timeout_s`, default 30s** - separate connect/read deadlines are not achievable (verified: `urllib.request.urlopen` takes a single `timeout`; `gh api`/`glab api` expose none). HTTP applies it per socket op; CLI applies it as a total process deadline. Max 2 retries on `rate_limited` only, backoff capped 30s, concurrency cap 4. TLS on by default; `sslVerify: false` honoured but never silent.

**Credential precedence is provider-specific, copied from the epic** - there is no generic "Keychain" rung and flow-next never implements a keyring, it reads env: GitHub `GH_TOKEN` -> `gh` config; GitLab `GITLAB_TOKEN` -> `glab` config; Linear `LINEAR_API_KEY`; Jira selects by the **persisted `authScheme`** (`cloud-basic` -> `JIRA_EMAIL`+`JIRA_API_TOKEN`; `bearer-pat` -> `JIRA_PAT`) rather than re-racing both sets each run, with `JIRA_BASE_URL` overriding the persisted `baseUrl`.

Transport mechanism per provider: GitHub/GitLab via their CLI (host+auth resolution already lives there); Linear/Jira via stdlib `urllib` (no CLI in the dependency set, keeps zero-dependency).

**Classification is per-adapter and tabulated.** `401/403 = auth` is insufficient: GitLab returns 403 for both a bad token and a licence-gated `is_blocked_by`, and Linear rate limiting arrives as a GraphQL error over HTTP 400.

Result envelope, exhaustive class enum, fixed numeric exit codes. JSON on stdout, human notes on stderr.

## Acceptance
- [ ] Request/Response match the epic schema EXACTLY, incl. `provider`, `op`, and separate connect/read timeouts
- [ ] Executor returns `Response | TrackerError`; no transport-native exception escapes
- [ ] GraphQL-over-200/400 normalized in the executor
- [ ] Per-adapter classification table: GitLab 403+licence-body -> capability, bare 403 -> auth; Linear GraphQL 400 -> rate_limited
- [ ] Bounds asserted: single `timeout_s` (HTTP per-op vs CLI process deadline), 2 retries, backoff clamp, concurrency 4
- [ ] Provider-specific credential precedence implemented exactly; NO generic Keychain rung
- [ ] Jira selects credentials by persisted `authScheme`; behavior defined when both sets are present
- [ ] Redaction at the boundary; no token in any log/receipt/error (test)
- [ ] `sslVerify: false` honoured and recorded, never silent
- [ ] Content-bearing args never in argv (body with shell metacharacters)
- [ ] Envelope + class enum + numeric exit codes; JSON stdout, notes stderr

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

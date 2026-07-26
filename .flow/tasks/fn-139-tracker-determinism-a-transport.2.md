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

Transport route is per provider **and operation**: GitHub/GitLab via their CLI for ordinary calls; Linear/Jira via stdlib `urllib`. **GitLab uploads use the HTTP/multipart route** - `glab api -F file=@` produces invalid multipart (measured), so the CLI has no permitted upload path.

`Request.credential_policy` is explicit: `provider-auth` (default) | **`presigned-anonymous`** (attach nothing - Linear's presigned PUT targets a third-party asset host and must never receive the Linear key) | `none`. Credentials are dropped on any host-changing redirect.

**Classification is per-adapter and tabulated.** `401/403 = auth` is insufficient: GitLab returns 403 for both a bad token and a licence-gated `is_blocked_by`, and Linear rate limiting arrives as a GraphQL error over HTTP 400.

Result envelope, exhaustive class enum, fixed numeric exit codes. JSON on stdout, human notes on stderr.

## Acceptance
- [ ] Request/Response match the epic schema EXACTLY, incl. `provider`, `op`, and **exactly one** `timeout_s` (no connect/read timeout fields)
- [ ] Executor returns `Response | TrackerError`; no transport-native exception escapes
- [ ] GraphQL-over-200/400 normalized in the executor
- [ ] Per-adapter classification table: GitLab 403+licence-body -> capability, bare 403 -> auth; Linear GraphQL 400 -> rate_limited
- [ ] Bounds asserted: single `timeout_s` (HTTP per-op vs CLI process deadline), 2 retries, backoff clamp, concurrency 4
- [ ] Provider-specific credential precedence implemented exactly; NO generic Keychain rung
- [ ] `credential_policy` honoured: Linear presigned PUT carries ONLY presigned headers (no API key); asset retrieval DOES carry auth
- [ ] Credentials dropped on host-changing redirect; no silent cross-host follow with auth
- [ ] GitLab upload uses the HTTP/multipart route, never `glab api -F`
- [ ] Jira selects credentials by persisted `authScheme`; behavior defined when both sets are present
- [ ] Redaction at the boundary; no token in any log/receipt/error (test)
- [ ] `sslVerify: false` on the **HTTP** route is honoured and recorded (fails closed if it cannot be recorded)
- [ ] `sslVerify: false` on a **CLI** route is REJECTED, not silently ignored. Amended during review: the executor cannot honour it there, because `gh`/`glab` expose no TLS flag and rewriting a CLI call into the equivalent HTTP call needs endpoint knowledge that lives in the adapters (tasks .4/.6), not in the transport seam. Rejecting is the only honest option at this layer; silently proceeding would claim a guarantee the route cannot deliver. Routing CLI ops over HTTP when TLS is disabled is deferred to .4/.6, where the endpoints exist.
- [ ] Content-bearing args never in argv (body with shell metacharacters)
- [ ] Envelope + class enum + numeric exit codes; JSON stdout, notes stderr

## Done summary
Injected executor delivered as the single transport seam: adapters call execute(request) only.

- types.py: Request/Response/TrackerError, exhaustive ErrorClass (11 values incl. external_action_required), fixed exit codes 2-12, per-REQUEST CredentialPolicy (presigned uploads never carry the provider key). Adapters cannot set credential headers (post_init rejects).
- executor.py: one timeout field (HTTP per-socket, CLI total process deadline), rate-limited+idempotent-only retry (max 2), clamped untrusted backoff hints, origin-scoped redirect credential stripping, BoundedSemaphore concurrency cap at the shared boundary, TLS opt-out honoured-but-never-silent (refused on CLI routes and when the record sink is missing OR fails), glab stdout-noise strip, CLI status extraction so the classifier's branches are reachable, forbidden-route table (gitlab upload must be HTTP), CLI route independent of unused credential state.
- classify.py: per-provider tables over measured behavior - GitLab 403 licence vs auth, GitHub 403 rate limits, Linear GraphQL-over-200 rate limits with structured codes and per-bucket epoch-ms reset headers (slowest exhausted bucket wins), Jira XSRF-404, total fallback, malformed-body normalization.
- credentials.py: exact-name per-provider resolution (no keyring rung), host-scoped glab config token, Jira scheme selected by persisted authScheme, short credentials refused at resolution (ShortCredential -> auth class), floorless process-wide redactor.
- envelope.py: single stdout JSON envelope, typed details variants, recursive scrub of every outbound string (values, mapping keys, stderr notes).

9 impl-review rounds (codex): 20+ findings, all fixed and pinned by regression tests; final round SHIP with R5/R6/R7/R14 met, R4 deferred to .4/.6 by design.
## Evidence
- Commits: 92f5e428, 57ddc560, 3b893722, 9119e8f1, 954d7d2c, e3188bc5, 6e87d0ef, 71f912d5, dc3cbc51, 284fd328
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_executor test_tracker_package_import -q, python3 scripts/run_tests_parallel.py
- PRs:
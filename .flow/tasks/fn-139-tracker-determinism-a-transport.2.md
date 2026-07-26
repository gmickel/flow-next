---
satisfies: [R4, R5, R6, R7, R14]
---

# fn-139-tracker-determinism-a-transport.2 Injected request executor + adapter interface + result envelope
# fn-139-tracker-sync-determinism-flowctl-owns.2 Wire verbs: read/update/comment CRUD/label/assign + persist-external

## Description
Define the typed transport layer every adapter calls. No adapter calls `subprocess.run` or opens a connection directly - that seam IS the fake transport spec B tests against, so it is built here, not retrofitted.

Implement the result envelope, the exhaustive `class` enum, and the fixed numeric exit-code mapping so callers branch on structure, never on prose.

Security and bounds are part of the seam, not an afterthought: no shell, content via stdin/file, credentials never persisted or logged, explicit per-request timeout, bounded retry on `rate_limited` only using each adapter's own header shape, capped concurrency, TLS on by default.

## Acceptance
- [ ] Adapters call only the injected executor; a test asserts no direct subprocess/socket use in `flowctl_tracker/`
- [ ] Executor is substitutable with an in-process fake
- [ ] Result envelope + class enum + numeric exit codes implemented and asserted
- [ ] Content-bearing args never in argv (test with a body containing shell metacharacters)
- [ ] No credential appears in any log line, receipt, or error string (test)
- [ ] Timeout, bounded retry, concurrency cap, TLS default-on all asserted

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

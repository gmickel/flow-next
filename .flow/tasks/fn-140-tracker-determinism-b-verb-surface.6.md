---
satisfies: [R17, R18]
---
# fn-140-tracker-determinism-b-verb-surface.6 Cross-adapter conformance matrix + fault injection

## Description
Focused regression tests live with the code in the tasks above. This is the cross-cutting layer.

**Conformance matrix**: same verb, all four adapters, same assertions.

**Fault injection** for what no single task owns: the open pre-create window, post-write readback failure, scoped invalidation, lock race on `tracker.resolved`, retry exhaustion, rate-limit backoff (each adapter's own header shape - Linear complexity-based, GitHub 5000/hr, Jira 350).

Implement the Jira Data Center custom-key path from prose, **marked unverified** in code comment and spec (Jira Cloud enforces uppercase-alphanumeric max-10 keys and cannot reproduce it). Its live smoke is a separate externally-blocked follow-up, NOT a task here - a permanently-todo task would block spec close.

## Acceptance
- [ ] Conformance matrix covers every verb on all four adapters
- [ ] All six fault points covered
- [ ] Pre-create window tested as OPEN (documents the accepted gap; does not assert it closed)
- [ ] Rate-limit backoff asserted per adapter's own header shape
- [ ] Jira DC custom-key path implemented + marked unverified in code AND spec
- [ ] Full gate green

## Done summary
Cross-adapter conformance layer (grok-4.5 + host round; 2 codex rounds).

test_tracker_conformance.py: every wire verb (11) AND every spec-aware verb (create, create-first, persist-external, status, relate, sync-body) x all four adapters with one assertion set per verb; github attach asserts the capability GATE, persist-external asserts the linear-only provider gate BEFORE any request; FullVerbSurfaceGuard pins the complete granular surface (R18). Six fault points: open pre-create window tested as OPEN (documents the accepted duplicate, never asserts it closed), post-write readback failure across all four (prior merge base untouched), scoped invalidation via resolve_verb.run (statusIds preserved, capabilities stamp not freshened), tracker.resolved lock race (two scopes, both land), retry exhaustion (MAX_RETRIES+1 calls, retry_after surfaced), rate-limit backoff per adapter header shape (github 403 epoch-seconds, gitlab/jira Retry-After, linear slowest exhausted complexity bucket in epoch-ms). Jira DC custom-key path (R17): _jira_issue_key/_jira_project_key grammar (underscores, >10 chars, injection-safe JQL) wired through display addressing, list-open, lifecycle persist; marked UNVERIFIED on live DC in code + spec.

Review round 1 finding (matrix self-scoped to wire verbs only) fixed with the six spec-aware verb classes; round 2 SHIP.
## Evidence
- Commits: 2b977503, 4bd9c94c, 7dcb4e08
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_conformance -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs:
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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

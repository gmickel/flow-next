---
satisfies: [R16]
---
# fn-139-tracker-sync-determinism-flowctl-owns.11 DEFERRED: Jira Data Center custom-key smoke (needs DC instance)

## Description
**Deferred. Blocks nothing. Stays `todo` until its prerequisite exists.**

Jira Cloud enforces uppercase-alphanumeric project keys, max 10 characters, so it **cannot reproduce** a custom Data Center key like `MY_PROJECT-7` or any key over 10 chars. That is the display-only path that produced a P1 in PR #241 (an unmintable identifier looping forever because the issue already existed), and it is the one adapter behavior in this spec implemented from prose rather than measurement.

**Prerequisite:** a reachable Jira Data Center / Server instance with a custom-key project.

## Acceptance
- [ ] Oracle: minting from `MY_PROJECT-7` links display-only, and a rejected mint degrades to flow-first + attach rather than looping
- [ ] The `unverified` marker is removed from code comment and spec once measured
- [ ] If the prerequisite never materializes, the marker STAYS and this task stays open - it is never closed by assertion

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

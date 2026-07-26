---
satisfies: [R9, R11]
---
# fn-139-tracker-determinism-a-transport.6 Resolution: Linear + Jira (stateIds tiebreak, statusIds only)

## Description
Resolve `destination` + `capabilities` for **Linear and Jira**, plus their scoped-resolution tests.

Linear: `teamId`, `teamKey`, `stateIds{normalized -> stateId}`, `labelIds`. `type: started` maps to **two** states (In Progress, In Review), so `resolve --select <normalized>=<stateId>` persists a human's tiebreak, validated against live candidates. An ambiguous state returns `class: conflict` with **both candidates in the typed `details` variant**, not a prose message.

Jira: `baseUrl`, `projectKey`, `projectId`, `issueTypeId`, `apiVersion: 2`, `style`, and **`statusIds` only**. Transition ids are NEVER cached - `jira.md:738` states they are valid only from the current status, verified live (To Do / In Progress / Done each surfaced different ids). Transition re-fetch is spec B's concern.

## Acceptance
- [ ] Linear + Jira resolve every field in the Architecture table
- [ ] Jira persists STATUS ids only; no transition id is written to the cache (asserted)
- [ ] `resolve --select` validates against live candidates before persisting
- [ ] Ambiguous Linear state returns `class: conflict` with both candidates in typed `details`
- [ ] Capability truth table matches exactly for both providers
- [ ] Scoped resolution on nested paths (`destination.stateIds`, `destination.statusIds`) tested

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

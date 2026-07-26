---
satisfies: [R9, R11]
---
# fn-139-tracker-determinism-a-transport.6 Resolution: Linear + Jira (stateIds tiebreak, statusIds only)

## Description
Resolve `destination` + `capabilities` for **Linear and Jira**, plus their scoped-resolution tests.

**Normalized state vocabulary** (the keys `stateIds`/`statusIds` must cover, shared with fn-66's policy): `backlog`, `todo`, `in_progress`, `in_review`, `done`, `cancelled`. Only `todo`, `in_progress` and `done` are **required**. `backlog`, `in_review` and `cancelled` are optional - many real Jira workflows lack backlog or cancelled entirely, so requiring them makes completeness unreachable. A key may **alias** another's status where a workflow has fewer states; aliasing is recorded, not silent.

Linear: `teamId`, `teamKey`, `stateIds{normalized -> stateId}`, `labelIds{name -> id}`.
- `--select` is **slot-by-slot and repeatable**; selecting `in_progress` does not infer `in_review`. Conflict details carry the `normalized` slot plus candidates.
- Mapping algorithm: group live states by `type` (`backlog|unstarted|started|completed|canceled`), map type -> normalized key; where a type yields **exactly one** state, take it; where it yields **more than one** (`started` -> In Progress + In Review), the run is ambiguous and requires `--select`.
- `labelIds` is keyed by label **name**, lowercased; GraphQL results are **paginated** (`pageInfo.hasNextPage`) and must be fully drained, not first-page-only. `type: started` maps to **two** states (In Progress, In Review), so `resolve --select <normalized>=<stateId>` persists a human's tiebreak, validated against live candidates. An ambiguous state returns `class: conflict` with **both candidates in the typed `details` variant**, not a prose message.

Jira `issueTypeId` **precedence, matching the existing prose**: configured `perTracker.issueType` -> a type named `Task` -> the project's first non-subtask type. Validated against the live project; an unresolvable configured value is an error, not a silent fallback.

Jira: `baseUrl`, `projectKey`, `projectId`, `issueTypeId`, `apiVersion: 2`, `style` (enum: `next-gen` team-managed | `classic` company-managed), and **`statusIds` only**.
- Map via `statusCategory.key` (`new|indeterminate|done`) plus status name. Where several statuses share a category the slot is **ambiguous** and takes the same `--select` path as Linear; where a required status does not exist the run fails with `class: conflict` naming the missing slot.
- **Existing `perTracker.statusMap` entries are migrated** into `statusIds` where they resolve to a live status; entries that no longer resolve are dropped with a warning rather than carried forward or silently kept. Transition ids are NEVER cached - `jira.md:738` states they are valid only from the current status, verified live (To Do / In Progress / Done each surfaced different ids). Transition re-fetch is spec B's concern.

## Acceptance
- [ ] Normalized vocabulary implemented; the five required keys present, `in_review` optional
- [ ] Linear label pagination fully drained (test with >1 page)
- [ ] Existing `statusMap` migrated into `statusIds`; unresolvable entries dropped with a warning
- [ ] Malformed existing config handled without crashing
- [ ] Linear + Jira resolve every field in the Architecture table
- [ ] Jira persists STATUS ids only; no transition id is written to the cache (asserted)
- [ ] `resolve --select` validates against live candidates and resolves exactly ONE slot; repeatable; re-select overwrites
- [ ] Jira `issueTypeId` precedence: configured -> Task -> first non-subtask; unresolvable configured value errors
- [ ] Only todo/in_progress/done required; backlog/in_review/cancelled optional; aliasing recorded
- [ ] Ambiguous Linear state returns `class: conflict` with both candidates in typed `details`
- [ ] Capability truth table matches exactly for both providers
- [ ] Linear and Jira capabilities are STATIC: no TTL re-probe is implemented for either (asserted)
- [ ] Scoped resolution on nested paths (`destination.stateIds`, `destination.statusIds`) tested

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

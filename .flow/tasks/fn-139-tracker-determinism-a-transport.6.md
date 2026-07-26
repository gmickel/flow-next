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
- [ ] Normalized vocabulary implemented; **three required** slots (`todo`, `in_progress`, `done`); **three optional** (`backlog`, `in_review`, `cancelled`)
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
Linear + Jira resolution, the normalized vocabulary, and the flowctl tracker resolve verb.

- states.py: shared six-slot vocabulary (todo/in_progress/done required) with an explicit PER-PROVIDER assignment policy. linear = type-only per the spec's mapping algorithm: >1 started states are ambiguous even with obvious names, --select resolves exactly one slot, no cross-slot inference, in_review never auto-fills. jira = category pools + sanctioned name hints + single-remaining rule. Human tiebreaks survive refresh; dead ids dropped with warning.
- providers/linear.py: teamId/teamKey/labelIds destination (pagination fully drained with a progress guard: repeated cursor fails, 50-page ceiling); stateIds via type pools; static capabilities.
- providers/jira.py: baseUrl (JIRA_BASE_URL override) / projectKey / projectId / issueTypeId (configured -> Task -> first non-subtask, configured-unresolvable errors, status scope REQUIRES the resolved issueTypeId - never first-entry) / apiVersion pinned 2 / style enum; statusIds ONLY (no transition id ever cached, asserted); legacy statusMap vocabulary migrated (planned/in-progress/in-review/verified/wontfix) with warnings for dropped/unknown keys; malformed statusMap tolerated.
- resolve_verb.py + flowctl tracker resolve CLI: explicit backfill (absent scopes only), --refresh, --scope, --select (validated INSIDE the transaction so the fingerprint covers a mid-select repoint; merge inside the lock via finalize_fn; re-select overwrites; out-of-pool select recorded as alias). Malformed config shapes return the envelope, never a traceback.
- resolvedAt completeness requires the three required slots in stateIds/statusIds.

2 review rounds (codex): round 1 found 7 (ambiguity-contract bypass, legacy-key gap, select TOCTOU, first-entry issue type, shape crashes, pagination loop, env bleed) - all fixed and pinned; round 2 SHIP.
## Evidence
- Commits: abf86c70, e1d4c19e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolution_linear_jira -q, python3 scripts/run_tests_parallel.py
- PRs:
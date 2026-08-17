---
satisfies: [R5]
---
# fn-199-issue-sweep-pilot-worktreereused-branch.3 Docs + changelogs for the sweep

## Description
1. plugins/flow-next/docs/flowctl.md: add list-states to the wire verb CLI listing (~line 1444 block) and its behavior (read-only, completeness signal, provider scope) near the wire verb reference; note the resolve-vs-list-states distinction (resolve repairs and writes; list-states detects and never writes). Document the actual shipped shape, not the spec's generic sketch: Jira's endpoint is the hardcoded `/rest/api/2/project/<key>/statuses` (the statuses endpoint is stable on v2; only `list_open` forks to a v3 search) — do not describe it as version-templated (`/rest/api/<v>/…`); an invalid-format `projectKey` returns `INVALID_INPUT`, matching `list_open`'s taxonomy — one line noting that parity is enough. Also document that a malformed/id-less state node in the provider response is a typed `TRANSPORT`/`malformed_body` error on BOTH providers — never a silently shrunken list returned with `complete:true`. <!-- Updated by plan-sync: fn-199.2 hardcoded Jira to /rest/api/2 (not version-templated) + malformed-node handling is TRANSPORT/malformed_body on both providers -->
2. plugins/flow-next/docs/tracker-sync.md: wire section entry for list-states alongside list-open/relation-list.
2b. plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md: add a `list-states` row to the "Wire verbs" table (context-free, no locator — output is the exhaustive `{"states":[...], "complete":bool}` shape, never local state). Also fix the now-inaccurate blanket claim "Pagination is exhausted inside the adapter" immediately below that table — `list-states` is a **sanctioned exception**: it returns a single page plus an explicit `complete` completeness signal instead of draining pagination internally, on both providers. State that exception inline rather than silently leaving the old absolute sentence standing. <!-- Updated by plan-sync: fn-199.2 review flagged adapter-interface.md wire-verb table + pagination-exhausted claim as stale -->
3. Pilot docs: if any doc restates the old default-branch or MERGED->NEEDS_HUMAN rules (check plugins/flow-next/docs/ for restatements), update to the property-based rules. Note: task .1 shipped the all-done discriminator as **head identity** (`git rev-parse <branch>` vs the newest merged PR's `headRefOid`) rather than the spec's `git rev-list --count` option, because land squash-merges (a rev-list ancestry count against the default branch would read fully-shipped work as unshipped). Describe the shipped head-identity rule in any doc text you write or touch — do not restate `git rev-list --count` from the spec's API Contracts/Decision Context sections. <!-- Updated by plan-sync: fn-199.1 used head-identity (headRefOid vs branch head) not rev-list -->

4. Repo CHANGELOG.md ## Unreleased: three user-outcome-first entries crediting @sn-furali (#354, #355, #356), per agent_docs/releasing.md ordering rules.
5. Docs-site changelog (~/work/flow-next.dev): stage an Unreleased entry in the customer register (problem-first, per the register rules; see last 20 entries as exemplars). Commit in that repo but do not publish/release.
No version bump anywhere (batched releases).

## Acceptance
R5: flowctl.md + tracker-sync.md + skills/flow-next-tracker-sync/references/adapter-interface.md document list-states, including the Jira hardcoded-v2-endpoint/INVALID_INPUT-parity note, the both-providers malformed-node TRANSPORT behavior, and the adapter-interface.md wire-verb-table + pagination-exhausted-exception fix; any doc restating the old pilot rules is updated; repo CHANGELOG Unreleased credits @sn-furali for all three issues; docs-site Unreleased entry staged in the customer register; no version manifests touched. Full docs-tree gate green (run_tests_parallel).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

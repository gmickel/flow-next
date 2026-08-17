---
satisfies: [R5]
---
# fn-199-issue-sweep-pilot-worktreereused-branch.3 Docs + changelogs for the sweep

## Description
1. plugins/flow-next/docs/flowctl.md: add list-states to the wire verb CLI listing (~line 1444 block) and its behavior (read-only, completeness signal, provider scope) near the wire verb reference; note the resolve-vs-list-states distinction (resolve repairs and writes; list-states detects and never writes).
2. plugins/flow-next/docs/tracker-sync.md: wire section entry for list-states alongside list-open/relation-list.
3. Pilot docs: if any doc restates the old default-branch or MERGED->NEEDS_HUMAN rules (check plugins/flow-next/docs/ for restatements), update to the property-based rules.
4. Repo CHANGELOG.md ## Unreleased: three user-outcome-first entries crediting @sn-furali (#354, #355, #356), per agent_docs/releasing.md ordering rules.
5. Docs-site changelog (~/work/flow-next.dev): stage an Unreleased entry in the customer register (problem-first, per the register rules; see last 20 entries as exemplars). Commit in that repo but do not publish/release.
No version bump anywhere (batched releases).

## Acceptance
R5: flowctl.md + tracker-sync.md document list-states; any doc restating the old pilot rules is updated; repo CHANGELOG Unreleased credits @sn-furali for all three issues; docs-site Unreleased entry staged in the customer register; no version manifests touched. Full docs-tree gate green (run_tests_parallel).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

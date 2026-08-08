---
satisfies: [R6]
---
# fn-175-task-shape-tasks-are-the-delegation.2 CHANGELOG Unreleased entry (task-shape doctrine)

## Description
Extend the Unreleased CHANGELOG section with the fn-175 entry.

**Size:** S
**Files:** `CHANGELOG.md`

### Approach
- Bullets under `## Unreleased` > `### Changed`: tasks are now the delegation payload - concrete files, approach, and task-scoped acceptance that let a cheaper implementer build without re-deriving design decisions; tasks reference the spec's R-IDs instead of restating its context (replay agents wrote tasks at ~3x the fleet norm, and the bloat was paraphrased spec context that drifts); executors always receive the task together with the full parent spec, so nothing is lost; tasks can declare a touches: line (paths they expect to modify) for later concurrency planning.
- No speed claims; cost/quality framing. No version bump. Done summary notes docs-site owed at batched release.

### Acceptance
- [ ] Unreleased bullets present, no em dashes, no speed claims
- [ ] No version manifests touched
- [ ] Done summary notes docs-site owed at batched release

## Acceptance
- [ ] TBD

## Done summary
Added the task-shape Unreleased bullet (delegation payload, R-ID references over restatement, both-channels guarantee, touches: line), cost/quality framing, no em dashes, no version manifests. OWED AT BATCHED RELEASE: flow-next.dev changelog entry.
## Evidence
- Commits: 61845a95
- Tests: docs-only; register read-through
- PRs:
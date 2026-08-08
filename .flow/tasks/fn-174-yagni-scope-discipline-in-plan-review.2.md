---
satisfies: [R4]
---
# fn-174-yagni-scope-discipline-in-plan-review.2 CHANGELOG Unreleased entry + docs-site check

## Description
Stage the user-facing release notes for fn-174 under `## Unreleased` and walk the docs surfaces.

**Size:** S
**Files:** `CHANGELOG.md`

### Approach
- `CHANGELOG.md` currently has no `## Unreleased` section (top entry is 3.17.0) - add one above it, keep-a-changelog format, `### Changed`. Entry is user-outcome-first per `agent_docs/releasing.md` (read its ordering + rejection rules): plans now bind to scope minimality (every task traces to an R-ID, every R-ID to the request; unrequested capabilities become one-line Boundaries exclusions; structural elimination preferred over risk machinery), plan review flags overengineering as a finding on both backends' rubrics, workers build to the AC not past it - citing the flow-efficiency replay campaign evidence (-43% output tokens / -57% cost at above-baseline reviewed quality). No em dashes (house style: plain hyphens).
- NO version bump, NO bump.sh (batched release later; the release itself is a separate goal step after all five specs land).
- Docs check (do, then record): re-scan `plugins/flow-next/docs/` and root `README.md` for surfaces documenting plan/plan-review/worker discipline; expected result is no updates needed (spec-template.md documents scaffold structure, not discipline prose; doc-index tracks releases). Record the actual result in the done summary.
- Done summary MUST note: flow-next.dev changelog entry is owed at the batched release.

### Acceptance
- [ ] `## Unreleased` entry present, cites replay-campaign evidence, user-outcome-first register, no em dashes
- [ ] No version manifests touched
- [ ] Docs re-scan performed and result recorded in the done summary
- [ ] Done summary notes the docs-site entry is owed at the batched release
## Acceptance
- [ ] Unreleased CHANGELOG entry cites replay-campaign evidence, user-outcome-first, no em dashes (R4)
- [ ] No version manifests touched
- [ ] Docs re-scan result + owed docs-site entry recorded in done summary
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

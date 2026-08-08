---
satisfies: [R4]
---
# fn-177-authoring-hygiene-author-as-file.2 CHANGELOG Unreleased entry (cost/quality framing, no speed claims)

## Description
Extend the existing `## Unreleased` CHANGELOG section with the fn-177 entry.

**Size:** S
**Files:** `CHANGELOG.md`

### Approach
- Add bullets under the existing `## Unreleased` > `### Changed` (created by fn-174): planning documents are now authored as files and revised with span edits instead of re-emitted heredocs (measured -13% cost in both A/B pairs); spec examples are the contract - implementations may not add fields to a shown shape (kills a twice-caught deviation class); workers run focused tests while iterating and the full suite exactly at the existing gates (measured 54% of full-suite runs were redundant at 3x targeted cost).
- HARD BOUNDARY: no speed/latency/token-savings-as-speed claims - cost and quality framing only (the campaign falsified the speed claims).
- No version bump. Done summary notes the docs-site entry rides the batched release.

### Acceptance
- [ ] Unreleased bullets present, cost/quality framing, zero speed claims, no em dashes
- [ ] No version manifests touched
- [ ] Done summary notes docs-site owed at batched release

## Acceptance
- [ ] TBD

## Done summary
Extended the Unreleased CHANGELOG section with three bullets (author-as-file, examples-are-exhaustive, tiered test runs), cost/quality framing only, zero speed claims, no em dashes, no version manifests touched. Docs re-scan: no repo docs beyond CHANGELOG (spec-template.md documents scaffold structure; the new template comment needs no doc-site page change until the batched release). OWED AT BATCHED RELEASE: flow-next.dev changelog entry.
## Evidence
- Commits: c272225c
- Tests: docs-only; read-through against agent_docs/releasing.md register rules
- PRs:
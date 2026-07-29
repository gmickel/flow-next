---
satisfies: [R6, R7, R8]
---
# fn-136-structured-review-artifact-schema-in.6 Structured PR cognitive-aid artifact + GitHub Markdown walkthrough

## Description
Implement the shared PR cognitive-aid data contract and GitHub Markdown approximation described by fn-136.

**Size:** L

**Files:** make-pr canonical skill/workflow and Codex mirror; flowctl receipt/artifact validation and write plumbing; cognitive-aid export/fixtures; focused tests.

### Approach
- Add the versioned `pr_cognitive_aid.changeWalkthrough` schema exactly as specified. The make-pr host agent owns thesis, logical grouping and order; flowctl only validates and persists.
- Compose groups from existing cognitive-aid inputs with claim provenance. Never add a second model call, deterministic intent classifier, commit-message narrative, or ungrounded file path.
- Implement the full-render trigger from human-review lines/non-generated file count. Keep the current compact body below threshold unless multiple logical stages materially help.
- Render `## The change, top to bottom` in GitHub-supported Markdown: proof table, legend, ordered details groups, file tables, diff links, deliberate non-changes and verification. Preserve the existing risk-ranked Review plan.
- Keep raw diff excerpts out of Markdown by default. Generated/mechanical paths are excluded from threshold math and collapsed separately.
- Run sync-codex twice and the focused make-pr/reached-path/receipt tests.
## Acceptance
- [ ] A versioned, bounded `pr_cognitive_aid.changeWalkthrough` artifact validates and persists through existing Flow-Next receipt/artifact plumbing with no extra model call (R6).
- [ ] Markdown renders the required hierarchy and diff links while preserving the existing review plan and raw-diff privacy boundary (R7).
- [ ] Threshold, generated/mechanical exclusion and collapse behavior are fixture-tested (R8).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

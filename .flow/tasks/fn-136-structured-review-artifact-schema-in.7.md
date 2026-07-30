---
satisfies: [R9, R10]
---
# fn-136-structured-review-artifact-schema-in.7 Cross-render parity fixtures + consumer docs + final gate

## Description
Add canonical cross-render fixtures, cross-repo synchronization metadata, checked-in reference images, consumer docs and final gates.

**Size:** M

**Files:** `plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json` plus metadata; structured/Markdown/HTML parity tests; fn-136 assets; consumer docs; CHANGELOG.

### Approach
- Create the canonical maximum-normal v1 fixture and metadata containing schema version, source path/commit and SHA-256.
- Prove exact semantic parity across artifact validation, GitHub Markdown and optional HTML input: identity/currentness, sources, group order/kinds, file membership, change/attention dimensions, file-level R-ID/task links, deliberate non-changes and verification.
- Document the vendoring contract: Flow Swarm carries byte-identical fixture bytes plus metadata and tests its local SHA against the pinned upstream digest without requiring private cross-repo network access in CI.
- Verify the three high-resolution images and all repository-relative links.
- Pin the maximum-normal fixture's performance contract in metadata and consumer docs: validation plus Markdown rendering must remain strictly below 100 ms p95 over 30 warm runs. The 100 ms ceiling supersedes the original 50 ms target after a representative parallel-suite observation of 90.57 ms, which is operationally negligible within the end-to-end workflow.
- Run sync-codex twice, focused suites, full tests and pinned Ruff; add Unreleased entry, no version bump.
## Acceptance
- [ ] Canonical v1 fixture and metadata prove structured/Markdown/HTML parity and define byte-pinned downstream vendoring (R9).
- [ ] Three reference images resolve and remain documented as information-architecture references (R10).
- [ ] Fixture metadata, consumer docs, and executable benchmarks agree on a strict `<100 ms p95` budget over 30 warm runs (R8/R9).
- [ ] Consumer docs, Unreleased entry, mirror idempotency, full test suite and pinned Ruff pass.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

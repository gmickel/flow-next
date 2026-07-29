---
satisfies: [R9, R10]
---
# fn-136-structured-review-artifact-schema-in.7 Cross-render parity fixtures + consumer docs + final gate

## Description
Add cross-render semantic parity fixtures, checked-in reference images, consumer documentation and final gates.

**Size:** M

**Files:** golden make-pr fixtures; fn-136 spec assets; receipt/memory/HTML-artifact consumer docs; tests; CHANGELOG Unreleased; any generated Codex mirror changes from task 6.

### Approach
- Create one golden logical walkthrough fixture consumed by structured artifact validation, GitHub Markdown rendering and optional HTML input tests. Assert exact group order, kinds, file membership, R-ID/task links, deliberate non-changes and verification facts.
- Check in the three high-resolution reference images under `.flow/assets/pr-aid/` and verify all spec-relative links resolve.
- Document additive schema/version/fallback behavior for cockpit-class consumers. Keep product naming neutral in Flow-Next.
- Run sync-codex twice, focused suites, `python3 scripts/run_tests_parallel.py`, and `uvx ruff@0.16.0 check .`. Add an Unreleased entry, no version bump.

## Acceptance
- [ ] One golden fixture proves semantic parity across structured artifact, Markdown and optional HTML input (R9).
- [ ] All three reference images are checked in, linked from fn-136 with valid relative paths and documented as information-architecture references (R10).
- [ ] Consumer docs, Unreleased entry, mirror idempotency, full test suite and pinned ruff gate pass.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

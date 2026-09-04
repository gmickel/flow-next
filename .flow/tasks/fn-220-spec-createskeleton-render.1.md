---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-220-spec-createskeleton-render.1 Implement spec create/skeleton render templates/spec.md

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`flowctl spec create` and `flowctl spec skeleton` now render the canonical `templates/spec.md` (YAML frontmatter stripped) through the documented override cascade `SPEC.md` -> `spec.md` -> bundled, first match wins; the legacy six-heading `SPEC_SKELETON_TEMPLATE` constant is deleted and `spec_skeleton_text()` / `create_epic_spec()` keep their signatures (R1, R2). The cognitive-aid exporter accepts read-only heading synonyms (`Overview`/`Context`, `Boundaries / non-goals`/`Non-goals`, any-case `Decision context`; the acceptance scanner already matched `## Acceptance`) with the canonical heading preferred when both exist (R3). The R22 skeleton baseline moved to the template itself: `test_r22_invariant` computes the expectation from the template, the `SPEC_SKELETON_TEMPLATE` pin was removed from `test_prompt_text_pinned` with the rationale in the commit message, and CHANGELOG carries an Unreleased Changed entry (R4). `flowctl validate` appends one `legacy spec headings (...) - prefer templates/spec.md` warning per spec that parses only through synonyms, never an error (R5). Docs updated: `docs/flowctl.md` (spec create / skeleton), `docs/spec-template.md` (cascade now applied by flowctl), `templates/spec.md` header note (R6). New `test_spec_template_cascade.py` plants each override in a temp git repo and covers bundled default, SPEC.md-over-spec.md precedence, CRLF normalization, exporter synonyms, and the validate warning. Implemented by grok-4.6 over the headless bridge in two runs, then five host-review rounds (fable-5.1, cross-family) drove four conductor fix passes: comment-masked scanners with fences as a locator, single-read template resolver, template hash pin, and the fence-first body anchor; a full 217-spec export sweep showed zero regressions. The conductor replaced a duplicate `git rev-parse` subprocess with the memoized `get_repo_root()` (frozen subprocess-inventory test), regenerated the tracker manifest and codex mirror, and ran the full gate.
## Evidence
- Commits: 15f9523ab7b727de72e15451e99107f22d6f8ec1, 8e55d207199cc2c47203310baa40b91b5ef492c3, 01e8b76b05ecf9252c6d444ce8f332be1e983e2e, 43e91546c9be3676ea50dfee81f8d72025b81292, 26adfabdef0e22423fca8e300b582a3d0a5455a5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_spec_template_cascade test_r22_invariant test_prompt_text_pinned test_acceptance_criteria_parser test_template_canonical test_review_prompt_constraints test_tracker_package_import -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh && ./scripts/sync-codex.sh, python3 scripts/gen_tracker_manifest.py
- PRs:
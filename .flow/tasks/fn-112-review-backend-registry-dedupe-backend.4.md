# fn-112-review-backend-registry-dedupe-backend.4 Fenced-JSON output contract + extensibility proof + docs

## Description
Fenced-JSON reviewer output contract + registry extensibility proof + docs + CHANGELOG + full gate.

**Size:** M
**Files:** both flowctl.py copies, the task-3 prompt templates (add the JSON-block instruction), tests, plugins/flow-next/docs/flowctl.md + docs/orchestration.md, CHANGELOG.md

### Approach

- Reviewer output contract: templates instruct backends to emit ONE fenced ```json block carrying tallies/findings (suppressed_count, classification counts, unaddressed R-IDs, deep findings). parse_suppressed_count / parse_classification_counts / parse_unaddressed_rids / parse_deep_findings (~560 LOC tolerant prose regex) shrink to json.loads + schema validation WITH the old regex path kept as explicit fallback ONLY if a reviewer omits the block (log which path fired; the fallback is deletable in a later spec once field data shows the block is reliable). The <verdict>SHIP/NEEDS_WORK</verdict> tag contract is UNCHANGED - it stays the sanctioned edge.
- Extensibility proof: a test that registers a hypothetical 4th backend using only a registry entry (mock run_exec) and drives cmd_backend_review through impl kind end-to-end.
- Skill prose: update impl-review/plan-review/completion-review workflow files where they relied on the standalone status-write calls task 2 made handler-internal (keep the standalone commands documented - they still work).
- Docs: flowctl.md review-command section reflects the registry architecture; orchestration.md note that backends are registry entries.
- CHANGELOG [Unreleased] rider: one entry for the whole spec (register-conformant, no em dashes, no version bump).
- Final gate (host runs it, but leave the repo green): full parallel suite + focused review suites.

### Acceptance

- [ ] Fenced-JSON contract parsed via json.loads + schema; prose-regex demoted to logged fallback; verdict tag untouched
- [ ] 4th-backend registry-entry test passes
- [ ] Docs updated; CHANGELOG Unreleased entry present
- [ ] Focused suites green: test_backend_spec.py, test_unaddressed_rids_parser.py, test_review*.py, test_codex_verdict_extraction.py
- [ ] Both copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

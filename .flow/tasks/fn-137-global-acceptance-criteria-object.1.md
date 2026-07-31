---
satisfies: [R1]
---
# fn-137-global-acceptance-criteria-object.1 criteria.md grammar + flowctl criteria plumbing

## Description
The criteria object and its deterministic plumbing.

**Size:** S

**Files:** flowctl.py (criteria subcommand: list --json w/ validation; dual-copy checklist applies), tests.

### Approach
- Grammar: `- **G<N>:** <criterion prose>` (mirrors R-ID form; optional trailing scope hint in prose); parse .flow/criteria.md when present; validate unique ids, non-empty, sequential-not-required.
- `flowctl criteria list --json` -> [{id, text}]; absent file -> [] + ok exit (silent no-op everywhere else).
- Zero-cost-absent proof: stage the assertion now as "completion-review prompt assembly output contains no criteria block marker when .flow/criteria.md is absent" - the marker is the canonical heading `## Global acceptance criteria`, exposed as a shared flowctl constant that .2's injection MUST use (test greps the constant, not a re-typed literal). Vacuously green in this task (no injection exists yet), load-bearing after .2. No placeholder plumbing beyond the test + constant.

## Acceptance
- [ ] Grammar parses + validates; absent = clean empty (R1).
- [ ] Focused tests; Quick commands recorded.

## Done summary
Added `flowctl criteria list --json`: parses `.flow/criteria.md` with the G-ID grammar (`- **G<N>:** prose`; unique ids, non-empty text, gaps allowed; absent file -> empty list with ok exit) and exposed the canonical `## Global acceptance criteria` marker as the shared `GLOBAL_CRITERIA_HEADING` constant, with a zero-cost-absent prompt-assembly test that greps the constant (vacuously green until fn-137.2's injection). Full propagation done: help fast-path + HELP_SHA256 + tracker MANIFEST regenerated and .flow/bin dual copies refreshed. Implementation delegated to grok-4.5 via the cursor-agent bridge per run directive; diff reviewed and finished by the orchestrator.
## Evidence
- Commits: 273ab221ac3a65aec5f53f90c699c460fc382dab
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_criteria test_flowctl_surface test_startup_bootstrap test_bin_launcher_parity test_tracker_distribution test_prompt_text_pinned -q (65 tests OK), uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/tests/test_criteria.py plugins/flow-next/tests/test_flowctl_surface.py (clean), baseline: none (spec defines no Quick commands; focused suites per repo convention, full suite at final gate), python3 scripts/run_tests_parallel.py (full suite: files=165 ran=3452 failures=0 errors=0; green receipt 273ab221-unittest recorded)
- PRs:
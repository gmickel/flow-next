---
satisfies: [R1, R2, R3, R4]
---
# fn-242-issue-sweep-glossary-offsets-zsh-merge.1 Implement Issue sweep: glossary offsets, zsh merge command, todo/backlog status rule

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Fixed the three swept issues: `parse_glossary_file` strips `_Avoid_`/`_Relates to_` in descending offset order so entries with both lines round-trip (#408); land's merge fence builds `MERGE_CMD` as an array from a command substitution so it word-splits under bash and zsh without eval, Codex mirror regenerated idempotently (#406); `decide()` noops a requested todo/backlog against `{flow: todo, tracker: backlog}` and status-sync.md notes `statusMap` is Jira/Linear-only (#375). One regression test per fix (`test_glossary_parse.py`, `test_land_merge_cmd_shell.py` runs the real fence under `bash --norc` and `zsh -f`, `TodoBacklogEarlyAgreement` in `test_tracker_status.py`); two existing static fence pins updated to the array form; CHANGELOG Unreleased carries three credited Fixed entries, no version bump.

Baseline note: the spec's `python3 -m pytest` Quick command is red for tooling (pytest not installed; repo is stdlib unittest) - unittest equivalents were green pre-edit and the full parallel suite is green post-edit with a receipt.

stage: impl-review - ran (codex gpt-6-astra medium, single correctness draw, SHIP first pass)
## Evidence
- Commits: ef5e4a1d0370ef806068c07614842a1f34a04c3d, 2eab4587e001bcabebbf783ccc7827467840131e
- Tests: baseline: red (python3 -m pytest tests/ -q -k 'glossary or policy or status' - pytest not installed; repo is stdlib unittest, unittest equivalents green pre-edit), python3 -m unittest discover -s plugins/flow-next/tests -p test_glossary_parse.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_land_merge_cmd_shell.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_tracker_status.py, bash scripts/sync-codex.sh (run twice, identical diff hash - idempotent), python3 scripts/gen_tracker_manifest.py --check, python3 scripts/run_tests_parallel.py (files=217 ran=4908 failures=0 errors=0; GREEN_RECEIPT 2eab4587-unittest)
- PRs:
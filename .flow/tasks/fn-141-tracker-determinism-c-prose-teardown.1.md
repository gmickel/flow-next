---
satisfies: [R1, R2]
---
# fn-141-tracker-determinism-c-prose-teardown.1 Prose reduction to transport-shape docs; five judgment surfaces

## Description
Reduce the adapter references and `steps.md` to transport-shape documentation. The skill calls `flowctl tracker <verb>`; it no longer contains invocations to execute.

`SKILL.md` names **exactly five** judgment surfaces with rationale: MCP rung, discovery ceremony, body-merge conflict adjudication, comment content synthesis, and recovery routing from a structured error. The earlier draft claimed four while its own table listed recovery as agentic.

Measurement is mechanical, not by eye: a test asserts zero executable-invocation matches (`gh api`, `glab api`, `curl -sS`, `POST /rest/api`) inside bash fences across an enumerated file set, and that the summed character count is >=150,000 below the baseline recorded in the test.

## Acceptance
- [ ] Zero executable-invocation matches in bash fences across the enumerated set
- [ ] Summed char count >=150,000 below the recorded baseline
- [ ] SKILL.md names exactly five surfaces with rationale for each
- [ ] Body-merge adjudication explicitly retained as agentic

## Done summary
Collapsed tracker-sync skill prose into deterministic transport contracts while
retaining exactly five rationalized agentic judgment surfaces. Added mechanical
teardown guards, migrated stale provider tests, refreshed Codex mirrors and
reached-path checks, and aligned facade event and comment normalization guidance
with production.
## Evidence
- Commits: 2020120404a3849b262684c3ba2056efbcf97304, 84a7f180976d2a467b75db79067651719fbd36f8, a87247667b03abed92260598b98e8f154d1e2c65
- Tests: python3 plugins/flow-next/tests/test_tracker_sync_prose_teardown.py -q, python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker_sync*.py' -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q, ./scripts/sync-codex.sh (twice, idempotent)
- PRs:
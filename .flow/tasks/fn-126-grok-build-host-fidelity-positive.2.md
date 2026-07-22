---
satisfies: [R4]
---
# fn-126-grok-build-host-fidelity-positive.2 Executable detection test + Codex mirror guard

## Description
Testability + Codex mirror. Add an EXECUTABLE detection test (plugins/flow-next/tests/test_setup_grok_host.py or extend the setup-host test): extract the Step-0 fenced bash from flow-next-setup/workflow.md and run it under fake-env fixtures - assert `GROK_AGENT=1` (no higher signal) -> PLATFORM=grok; inherited-env/precedence cases (DROID/CLAUDE/CURSOR present alongside GROK_AGENT) classify by the higher-precedence host; plain -> codex; no regression to the existing matrix. Update scripts/sync-codex.sh: the regenerated codex mirror of the setup workflow must render a real Codex host deterministically as `codex` (the mirror cascade carries NO grok rung - Codex consumes the mirror, canonical-file hosts consume canonical), enforced by a hard-fail sync guard (fn-100 pattern); regenerate the mirror. Covers R4.

## Acceptance
- Executable fixture runs the actual detection bash (not a prose regex): GROK_AGENT=1 -> grok; precedence cases correct; plain -> codex; Droid/Claude/Cursor/Codex unregressed.
- sync-codex hard-fail guard asserts the mirror setup cascade contains no grok rung / no GROK_AGENT branch; `./scripts/sync-codex.sh` twice-idempotent (byte-identical 2nd pass).
- Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_setup_grok_host test_setup_cursor_host -q`.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R4]
---
# fn-126-grok-build-host-fidelity-positive.2 Executable detection test + Codex mirror guard

## Description
Testability + Codex mirror. Add an EXECUTABLE detection test (plugins/flow-next/tests/test_setup_grok_host.py or extend the setup-host test): extract the Step-0 fenced bash from flow-next-setup/workflow.md and run it under fake-env fixtures - assert `GROK_AGENT=1` (no higher signal) -> PLATFORM=grok; inherited-env/precedence cases (DROID/CLAUDE/CURSOR present alongside GROK_AGENT) classify by the higher-precedence host; plain -> codex; no regression to the existing matrix. Update scripts/sync-codex.sh: the regenerated codex mirror of the setup workflow must render a real Codex host deterministically as `codex` (the mirror cascade carries NO grok rung - Codex consumes the mirror, canonical-file hosts consume canonical), enforced by a hard-fail sync guard (fn-100 pattern); regenerate the mirror. Covers R4.

## Acceptance
- Executable detection fixture runs the ACTUAL Step-0 bash: anchor-extract between the Step-0 heading and its first bash fence (assert exactly one match), scrub inherited host env vars, controlled HOME/PLUGIN_ROOT (temp Cursor install tree for the cursor fixture), append `printf '%s\n' "$PLATFORM"`. Assertions: GROK_AGENT=1 (no higher signal) -> grok; higher-signal-alongside-GROK_AGENT -> the higher host; plain -> codex; Droid/Claude/Cursor/Codex unregressed.
- sync-codex mirror replaces Step-0 with UNCONDITIONAL `PLATFORM="codex"` (not merely dropping the grok rung); hard-fail guard asserts the mirror Step-0 has no host-detection branches; executable MIRROR fixture asserts GROK_AGENT=1 + every other host signal still returns codex.
- `./scripts/sync-codex.sh` twice-idempotent (byte-identical 2nd pass).
- Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_setup_grok_host test_setup_cursor_host -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R3, R4, R7, R9]
---
# fn-145-opus-5-autonomous-seam-retune.2 Make delegation consent fully autonomy-aware

## Description
Make Work's Codex-delegation consent gate recognize the complete autonomous
marker family. With no persisted consent, autonomous execution must disable
delegation and continue the standard in-session Work path without asking.

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation-selection.md`
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`
- `plugins/flow-next/tests/test_codex_delegation_gates.py`
- `plugins/flow-next/tests/test_work_reached_path_routes.py`

### Approach

- Treat active Ralph, receipt, `FLOW_AUTONOMOUS=1`, and parsed
  `mode:autonomous` as identical no-question signals at every delegation ask
  site.
- Preserve existing persisted-consent, sandbox, `auto`/`ask`, and interactive
  behavior.
- Keep missing-consent fallback on standard Work; do not persist a synthetic
  decision or widen authority.

### Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/SKILL.md:40-50`
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation-selection.md:69-124`
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md:195-235,770-785`
- `plugins/flow-next/tests/test_codex_delegation_gates.py`

**Optional:**
- `.flow/specs/fn-95-surface-setup-version-mismatch-once-per.md`
- `.flow/specs/fn-103-delegation-diet-path-handoff-replaces.md`

### Key context

Only exact active values are headless: environment flags equal `1`, a nonempty
receipt path, or the parsed autonomous mode. Empty or `0` environment values do
not silently suppress an otherwise interactive consent flow.

## Acceptance
- [ ] Every Work delegation consent/ask site recognizes Ralph, receipt,
  `FLOW_AUTONOMOUS=1`, and parsed `mode:autonomous`.
- [ ] Each autonomous marker with absent consent disables delegation and
  continues standard Work without asking or writing consent/config.
- [ ] Persisted consent still enables the existing sandbox and decision modes.
- [ ] Interactive missing-consent behavior remains unchanged.
- [ ] Delegation-gate and Work reached-path tests cover the marker truth table
  and pass.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R1, R2, R3]
---
# fn-126-grok-build-host-fidelity-positive.1 Setup: GROK_AGENT detection rung + Grok host profile

## Description
Setup: add the positive Grok detection rung + the Grok host profile. In plugins/flow-next/skills/flow-next-setup/workflow.md platform-detection block: add `elif [ -n "${GROK_AGENT:-}" ]` -> `PLATFORM=grok` BEFORE the `else -> codex` fallback and AFTER the DROID/CLAUDE_PLUGIN_ROOT/CURSOR rungs (a real Droid/Claude/Cursor host that inherited GROK_AGENT from a parent grok shell must still classify by its own higher-precedence signal). Add a short rationale paragraph citing the probe evidence (GROK_AGENT=1 set by grok; ~/.grok and PATH rejected as non-signals). Then the Grok PROFILE across every PLATFORM consumer: docs snippet = `/flow-next-` slash syntax to CLAUDE.md (canonical target), copy mode, `.flow/bin/flowctl`, NO `.codex/agents` copy, NO Ralph offer/registration; consent-refresh a pre-existing wrong Codex `$flow-next-` marker block to the slash form (marker-scoped). Review menu on grok: offer `host` (fail-closed cross-family caveat) + rp/codex/copilot/cursor/none. Extend the host-native model-routing scaffold (currently PLATFORM=cursor-gated) to platform=grok, enumerating Grok's available models at setup (grok models / equivalent); document that Grok is single-native-family (grok-4.5) so native host review fails closed unless the writer is non-Grok, cross-family via bridges. Covers R1,R2,R3.

## Acceptance
- `GROK_AGENT` rung added before `else->codex`, after DROID/CLAUDE/CURSOR; ordering keeps inherited-GROK_AGENT hosts correctly classified.
- Probe evidence (GROK_AGENT=1) cited in the workflow rationale; ~/.grok + PATH explicitly noted as non-signals.
- grok profile: `/flow-next-` slash snippet to CLAUDE.md, copy mode, `.flow/bin/flowctl`, no `.codex/agents`, no Ralph; wrong Codex `$` block consent-refreshed marker-scoped.
- grok review menu offers `host` (fail-closed caveat) + external backends; host-native model-routing scaffold fires for platform=grok with enumerated grok models; single-family fail-closed behavior documented.
- NEEDS-HUMAN smoke: standalone grok session (not launched from another agent) -> `/flow-next:setup` reports platform=grok, writes the slash snippet to CLAUDE.md, no `.codex/agents`, Ralph not offered.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

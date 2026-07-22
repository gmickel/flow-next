---
satisfies: [R2, R3, R6]
---
# fn-126-grok-build-host-fidelity-positive.2 Implement the investigation-selected Grok setup profile

## Description
Implement the investigation-selected Grok setup profile. Update flow-next-setup/workflow.md; add test_setup_grok_host.py; touch sync-codex.sh only where the chosen branch requires; regenerate codex/skills/flow-next-setup/workflow.md. Audit EVERY PLATFORM consumer (manifest, setup mode, Codex-only agent copy, snippet family, docs target, review menu, model-routing target/syntax, Ralph handling, summary).
POSITIVE-SIGNAL branch: add `PLATFORM=grok` BEFORE the else->codex fallback, guarded against Codex-launched-from-a-Grok-shell.
NO-SIGNAL branch: the unknown-host path ASKS Grok-vs-Codex before Step 1 / any write; cancel or non-interactive ambiguity -> NEEDS_HUMAN; the Codex mirror stays deterministically Codex (does not inherit the ambiguity). Manual selection is run-scoped (no stale repo-level host override).
Grok profile: .claude-plugin/plugin.json, copy mode, .flow/bin/flowctl, CLAUDE.md default, claude-md-snippet.md, `/flow-next:*` slash syntax, NO .codex/agents, host-aware review menu incl. `host` (with the fail-closed cross-family caveat) + external backends, NO Ralph offer/registration. A pre-existing wrong Codex `$flow-next-*` marker block can be consentfully refreshed to the Grok slash snippet without touching text outside the markers.

## Acceptance
- Executable fixture matrix: Droid, Claude Code, Cursor, Codex, Grok, non-Grok-host-with-Grok-installed, Codex-from-Grok-shell.
- No PATH/home/config/hook-only var auto-classifies Grok.
- Grok -> slash/canonical-copy profile; Codex keeps `$flow-next-*` + Codex project setup.
- Wrong Codex-shaped marker consentfully refreshable to Grok slash snippet, marker-scoped only.
- Grok review menu includes `host` (fail-closed caveat) + external backends; no unsupported routing advertised; Grok skips Ralph entirely.
- New test <500 LOC; workflow edits narrow, no duplicated host blocks; sync-codex twice-idempotent.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

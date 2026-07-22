---
satisfies: [R3, R6]
---
# fn-123-cursor-first-class-experience-team.4 Cursor-host-aware setup: positive detection + model-routing scaffold

## Description
Make setup Cursor-host aware. (a) Detection: rewrite the Cursor branch in flow-next-setup workflow.md - currently `CURSOR_AGENT` + `.cursor-plugin/plugin.json` at PLUGIN_ROOT + `codex/` ABSENT. The codex-absence rung exists to reject the shared source tree, but it misclassifies marketplace repo-imports (which contain `codex/`). Replace with a positive signal that still rejects Codex-hosted-in-Cursor (inherited CURSOR_AGENT) and the raw source tree; cover the full matrix: whole-repo marketplace install, local script install, Codex launched inside a Cursor shell, Claude/Droid precedence. (b) Host-aware scaffolding on platform=cursor: review-backend menu leads with `host` (recommended), keeps all existing backends, labels `cursor` CLI circular/secondary; scaffold the AGENTS.md model-routing section with real Cursor slugs enumerated at setup time (host catalog or `cursor-agent --list-models`; the HOST AGENT picks the cheap-scout and cross-family-reviewer pins, never Python); routing rules: read-only scouts pinned cheap, host review pinned cross-family, everything else inherit; date-stamp + rerun-setup-to-refresh note. Cursor stays copy mode (`.flow/bin/flowctl`); no Ralph offer/registration on Cursor. Add `test_setup_cursor_host.py`; extend model-routing + snippet-lockstep tests; regenerate mirror.

## Acceptance
- Detection never depends on `codex/` absence; fixtures cover marketplace-import, local-install, Codex-in-Cursor-shell, and Claude/Droid ordering.
- On Cursor: menu leads with `host`; all existing backends selectable; cursor CLI labeled secondary; model routing offered without requiring any external bridge CLI.
- Generated AGENTS.md block: cheap pin for read-only scouts, cross-family pin for host review, inherit otherwise; carries verification date + refresh note.
- Cursor remains copy mode; no plugin-root/PATH assumption; no Ralph on Cursor; non-Cursor setup output and routing behavior unchanged.
- Focused suites green (`test_setup_cursor_host`, `test_model_routing_scaffold`, `test_setup_snippet_lockstep`); sync-codex twice-idempotent.


## Done summary
Positive Cursor detection: PLUGIN_ROOT resolved under ~/.cursor/ (pwd -P) replaces the codex/-absence rung; 4-case matrix documented (marketplace import w/ codex/ present, local install, Codex-in-Cursor-shell inherited env, Claude/Droid precedence). Host-aware setup on cursor: Host (Recommended) leads menu, cursor CLI relabeled circular/secondary, fn-97 codex-recommendation suppressed on cursor; AGENTS.md model-routing scaffold w/ host-enumerated slugs + cursor-agent --list-models fallback, cheap scout pin + cross-family REVIEW_PIN (TODO if unavailable), inherit default, date stamp + refresh note; no Ralph on Cursor (never offer/register). 42 tests green; mirror twice-idempotent. Reviewed by session model: approved.
## Evidence
- Commits: 4bed7e23
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_setup_cursor_host test_model_routing_scaffold test_setup_snippet_lockstep -q
- PRs:
---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-162-smoke-test-the-cursor-in-ide-browser.1 Correct cursor-ide-browser rung from the live pass

## Description
Rewrite drive rung 4 against Cursor host-cache playbook and 2026-08-13 live passes. Document probe-by-id, 16-tool inventory, MCP-drop recovery, and the R3 evidence gap. Mirror via sync-codex twice. No flowctl code.

## Acceptance
Skill + platforms.md + Codex mirror match the live inventory and probe-by-id contract; R3 console/network remain an explicit evidence gap on the ladder row; sync-codex twice is byte-idempotent.

## Done summary
Rewrote drive rung 4 against the Cursor host-cache playbook and 2026-08-13 live passes. Probe-by-id (`cursor-ide-browser`) replaces catalog-omit-as-absent; the 16-tool inventory is live (no invented `browser_console_messages`); MCP unregister mid-run is a partial pass; R3 console/network remain an explicit evidence gap on the ladder row. Codex mirror regenerated twice (byte-idempotent). Shipped as 3.32.2. Notable-updates list left untouched by request.
## Evidence
- Commits: d125ea573613d48e1c8c94ddfb24d0167b6bad9c
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_cursor_docs_contract -q, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh
- PRs:
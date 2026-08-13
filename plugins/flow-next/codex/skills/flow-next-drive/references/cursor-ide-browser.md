# cursor-ide-browser — rung 4 (Cursor host-native; detect, never depend)

Web-ladder rung 4 (SKILL.md Step 3). Cursor's built-in in-IDE browser, exposed as the `cursor-ide-browser` MCP. **No install, no `command -v`.** On a Cursor host with nothing else installed, prefer this already-present surface over instructing an install. Off Cursor it is simply absent → fall through. Detect, never depend.

> This is **Cursor's own in-IDE browser**, NOT the third-party `browser-tools-mcp`.

## Source of truth

Prefer Cursor's **host cache** over this file — it is version-matched to the installed Cursor, outside git, and materialized on first use (so its absence is not evidence the rung is missing):

```
~/.cursor/projects/<workspace-slug>/mcps/cursor-ide-browser/
  SERVER_METADATA.json      # {"serverIdentifier":"cursor-ide-browser","serverName":"cursor-ide-browser"}
  INSTRUCTIONS.md           # Cursor's own driving playbook (order, lock/unlock, CDP, vision)
  tools/<tool>.json         # 16 per-tool input schemas
```

Re-derive from that directory. Secondary/canonical public page: <https://cursor.com/docs/agent/tools/browser> (fetched 2026-08-13). This file is a router, not a copy of `INSTRUCTIONS.md`.

Live passes (2026-08-13, interactive Cursor on macOS): a flowmeter dashboard at `http://127.0.0.1:8788/` settled the 16-tool inventory, `viewId` (except `browser_tabs`), snapshot YAML, real screenshots, lock-on-existing-tab, and the MCP-drop flake. Follow-ups in this repo attached via id-probe; one re-probe after a drop restored the server, the next call dropped it again. A dedicated R3 target at `http://127.0.0.1:8762/` never loaded — MCP died after lock, before CDP. Per-step table: `.flow/artifacts/fn-162/live-pass.md`.

## Detection

On a Cursor host, **probe the server by exact id `cursor-ide-browser` at least once** (call any tool — typically `browser_tabs {action:"list"}`). The MCP catalog **can omit** it even when it is usable; a name-probe can return the full 16-tool surface right after a listing showed it missing. Catalog omission is not a negative. There is no install step.

## Order (load-bearing)

You **cannot** lock before a tab exists. If a tab already exists (`browser_tabs` list), lock **first**, before any interaction.

`browser_navigate` → `browser_lock {action:"lock"}` → interactions → `browser_lock {action:"unlock"}` when fully done.

`browser_navigate {url, viewId?, newTab?, position?, take_screenshot_afterwards?}`. **Omit `position`** for background automation so focus is preserved. Set `position: "active"|"side"` only when the user explicitly asks to reveal the browser.

`viewId` is a real param on every tool **except `browser_tabs`** (which targets by `index`). Shapes seen: `stable-browser-session/<hex>`, `glass-browser-<uuid>`. Omit it to use the last-interacted tab.

## Tools (16 — live 2026-08-13)

`browser_tabs`, `browser_navigate`, `browser_lock`, `browser_snapshot`, `browser_take_screenshot`, `browser_click`, `browser_fill`, `browser_type`, `browser_select_option`, `browser_press_key`, `browser_scroll`, `browser_drag`, `browser_mouse_click_xy`, `browser_highlight`, `browser_get_bounding_box`, `browser_cdp`.

There is **no** `browser_console_messages`. Schemas live in the cache `tools/*.json` — don't copy them here.

- **`browser_snapshot`** `{viewId, interactive, maxDepth, compact, selector, includeDiff, take_screenshot_afterwards}` — YAML is the structure source of truth; refs are opaque handles tied to the latest snapshot for that tab. `interactive:true`, `selector`, and `includeDiff` are real token-saving levers. Flowmeter snapshot 2026-08-13: comboboxes included `value` + `options` inline. Re-snapshot after every DOM change.
- **`browser_select_option {ref, values[]}`** — required for `<select>`.
- **`browser_take_screenshot`** attaches a real image (macOS save path seen: `/var/folders/.../T/cursor/screenshots/page-<ISO-timestamp>.png`). Prefer it over CDP `Page.captureScreenshot`.
- **`browser_type`**, **`browser_drag`**, **`browser_mouse_click_xy`** (coordinate click; prefer refs), **`browser_get_bounding_box`**.
- **`browser_cdp {method, params}` is real** (Cursor-documented). **Never `Input.*`** — denied: focus-sensitive in Electron webviews, routes input to Cursor UI. Also denied: browser-wide, storage, cookie, permission, download, target-management, filesystem-backed file-input, system-level, and CDP navigation/history-navigation methods. Large CDP responses are written to files — read focused sections, don't inline.

**Iframe content is unreachable** — only elements outside iframes can be interacted with. A `/flow-next:qa` scenario whose controls live in an iframe cannot be driven here; set `QA_OUTCOME=BLOCKED` with `blocked_reason` naming the unreachable iframe (do not invent evidence paths). Fall through to the QA receipt write.

Never repeat a failing action without new evidence. After ~4 failed attempts, **stop and report**.

## MCP drop (the real flake)

The failure mode is not garbage snapshots. The **whole MCP server unregisters mid-run** (`Error: MCP server does not exist: cursor-ide-browser`) while the Glass pane stays open and the page keeps serving. There is nothing to unlock.

Recover: **re-probe by id**. Observed 2026-08-13: one restoration in several attempts (list after a drop returned the tab; the next navigate dropped it again). Other drops in the same day: re-probe failed until the session ended. **Partial-pass stop is the expected outcome**; a restore is a long shot, not a loop. If it does return: `browser_tabs` list → re-lock → re-snapshot (refs are dead) → retry the single failed op. A dropped MCP can leave a tab **locked** — if the server returns, `browser_lock {action:"unlock"}`; if it does not, the Glass pane **Take Control** control is the only clear (lock-tool schema). Reopening the URL (e.g. `cursor-app-control` `open_resource`) does **not** bring the MCP back. This workspace never grew a `mcps/cursor-ide-browser/` cache dir even after successful list+lock — cache absence is not evidence of absence.

## Verify — unresolved (fn-162 R3)

This rung has no console/network MCP tool. Public docs (2026-08-13) say logs are written to files the agent greps, and network traffic is "currently only available in the Agent panel". Cursor's own `INSTRUCTIONS.md` lists `Log.enable` and `Network.enable` as CDP examples — **that is not live evidence**. A dedicated 2026-08-13 attempt against `http://127.0.0.1:8762/` (page emits `console.error` + `fetch('/fail')` → 500) locked the tab, then the MCP dropped before any CDP call returned; after one successful re-probe, navigate dropped it again and it stayed gone. **Do not claim console/network work because a CDP method name appears in a doc.**

Consequence: rung 4 **cannot** satisfy the drive `verify` contract (clean console + no failed API request) unaided. A `/flow-next:qa` pass that reaches this rung and cannot capture console + network MUST set `QA_OUTCOME=BLOCKED` with `blocked_reason` naming the missing channels (rung 4 has no console/network from the driven surface). Do not invent `console_path` / network path values. Screenshot + snapshot YAML remain the proven drive evidence; they do not make verify complete. Fall through to the QA receipt write (do not stop without a receipt).

## Operator precondition (approval)

Default **Manual approval** (Settings → Agents → Auto-Run) blocks every browser action on a human click — an unattended `/flow-next:qa` or pilot pass on this rung stalls. Allow-listed actions or Auto-run are required for unattended use. Upstream warns against Auto-run on untrusted code or unfamiliar sites (prompt-injection). Enterprise **Browser Origin Allowlist (v2.1+)**: `browser_navigate` and MCP tools are origin-gated; documented bypasses are link clicks, redirects, and JavaScript navigation from an allowed origin (<https://cursor.com/docs/agent/tools/browser>, 2026-08-13).

## Host limits

Reachable **only** from an interactive Cursor IDE session — not from `cursor-agent`, not from CI, never on a headless path. Off Cursor, absent. Detect, never depend. If no rung above this passes either, the terminal rung is **manual + screenshot relay** (SKILL.md Step 3, rung 5) — drive yourself and paste console errors + screenshots into chat. The pass still completes.

## Still unverified

- Console + network from the driven surface (CDP `Log.enable` / `Network.enable`, or the public-docs grep-a-log-file path) — see Verify.
- `Emulation.setDeviceMetricsOverride` for viewport.
- Storage clearing (`Runtime.evaluate` vs denied storage CDP).

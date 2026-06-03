# cursor-ide-browser — rung 4 (host-only, low rung: detect, never depend)

Web-ladder rung 4 (SKILL.md Step 3) — the **lowest non-manual rung**. Cursor's built-in in-IDE browser, exposed to the agent as MCP tools. **Host-only: it exists only when flow-next runs inside the Cursor IDE.** Known-flaky in agent driving → **detect, never depend**. Only reach for it when you're already in Cursor, the higher rungs (agent-browser, chrome-devtools-mcp, Playwright) aren't available, and you want its snapshot YAML + raw `browser_cdp` control.

> This is **Cursor's own in-IDE browser tool**, NOT the third-party `browser-tools-mcp`. Don't conflate them.

Canonical, version-matched docs (read these over this file when they disagree):

- Cursor browser tool: <https://cursor.com/docs/agent/tools/browser>

## Why it's a low rung

- **Host-only.** Runs as an MCP server inside the Cursor extension — no external install, but it only exists in Cursor. Outside Cursor (Claude Code/Codex/Droid terminals, cloud VMs, CI) it's simply absent → fall through to a higher rung or manual.
- **Known-flaky under agent control.** Treat lost control as expected: if `browser_snapshot` returns garbage or `browser_navigate` doesn't move the tab, recover once (unlock → list tabs → re-lock → retry one op); if it fails twice, **stop and report** — don't loop, switch rungs.
- **Prompt-injection risk** (per upstream): AI behavior on attacker-controlled pages can be unpredictable — Cursor gates actions behind Auto-Run approval modes (Manual / allow-listed / Auto-run).

## Detection

There's no `command -v` for it — it's an MCP surface. Detect by listing MCP tools and checking for the `browser_*` family (`browser_navigate`, `browser_snapshot`, …). If absent (the common case), it's not this rung — move on.

## Tool surface (universal flow → cursor tools)

```
browser_tabs action: list # observe
browser_navigate url, newTab # navigate
browser_lock viewId, action: lock|unlock # one agent only
browser_snapshot viewId, take_screenshot_afterwards: true # fresh refs (re-take after nav/click)
browser_click viewId, ref, element # act
browser_fill viewId, ref, value
browser_press_key viewId, key
browser_scroll viewId, direction, amount
browser_console_messages viewId # verify / evidence
browser_take_screenshot viewId # capture
browser_cdp viewId, method, params # raw CDP escape hatch
browser_highlight viewId, ref # debug a ref visually
```

- **Re-snapshot after every DOM change** — refs go stale like every other rung.
- **Never call `browser_cdp` with `Input.*` methods** (focus issues in Cursor's Electron host) — use the dedicated `browser_click` / `browser_fill` / `browser_press_key` tools.
- Viewport / storage via CDP: `browser_cdp Emulation.setDeviceMetricsOverride` (resize), `browser_cdp Runtime.evaluate` (read/clear `localStorage` / `sessionStorage`).
- State (cookies / localStorage / IndexedDB) persists per workspace, isolated per workspace.

## Drift-prone facts — **verify at build**

- The `browser_*` tool names and `viewId` parameter shape — Cursor's tool descriptors change; verify against the live tool list and the Cursor docs at build.
- Auto-Run approval modes and any Browser Origin Allowlist (enterprise) — version-gated; confirm against current Cursor docs.

## Limit

If no rung above this passes either, the terminal rung is **manual + screenshot relay** (SKILL.md Step 3, rung 5) — drive yourself and paste console errors + screenshots into chat. The pass still completes.

# fn-162 live pass — 2026-08-13

Interactive Cursor IDE on macOS. Rung 4 used by explicit direction (rung 1 `agent-browser` 0.27.0 was installed). Host cache (outside git, materialized on first use): `~/.cursor/projects/<workspace-slug>/mcps/cursor-ide-browser/` (`INSTRUCTIONS.md` + 16 `tools/*.json`). Secondary: <https://cursor.com/docs/agent/tools/browser> (fetched 2026-08-13).

No screenshot/console binaries retained in-repo: the user's screenshot reached the model and was saved under `/var/folders/.../T/cursor/screenshots/page-<ISO-timestamp>.png`; this session's tab was `about:blank` before the MCP dropped. Console/network were never captured (MCP drop before those channels).

## Pass A — flowmeter dashboard `http://127.0.0.1:8788/`

| Step | Call | Verdict | Actual shape |
|------|------|---------|--------------|
| observe | `browser_tabs {action:"list"}` | works differently | Tabs listed. `viewId` shapes: `stable-browser-session/<hex>` and `glass-browser-<uuid>`. |
| lock (existing tab) | `browser_lock {action:"lock", viewId}` | works as documented | `Browser locked.` + `{"locked":true}`. Lock-first on an already-open tab is required. |
| capture | `browser_take_screenshot {viewId}` | works as documented | Real image reached the model; saved to `/var/folders/.../T/cursor/screenshots/page-<ISO-timestamp>.png`. |
| snapshot | `browser_snapshot {viewId, interactive:true}` | works as documented | Snapshot YAML. 133 interactive refs (`root`, `e0`…`e132`). `Page URL` / `Page Title`. Comboboxes: `value` + `options` inline. |
| act | `browser_select_option {ref:"e1", values:["cursor"]}` | works differently then absent | Tool exists (`{ref, values[]}` required for `<select>`). Call returned `Error: MCP server does not exist: cursor-ide-browser`. Server stayed missing for the rest of the session. |
| verify (console) | *(no `browser_console_messages`)* | absent | Tool does not exist. CDP `Log.enable` not reached. |
| verify (network) | *(no network MCP tool)* | absent | Public docs: "currently only available in the Agent panel." CDP `Network.enable` not reached. |
| navigate | *(not separately recorded)* | — | Pass locked an already-open tab; order `navigate → lock` applies when no tab exists. |
| release | unlock | absent | MCP gone — nothing to unlock. Glass pane **Take Control** is the leftover-lock clear. |

## Pass B — this repo (catalog omit → attach → drop)

| Step | Call | Verdict | Actual shape |
|------|------|---------|--------------|
| detect (catalog) | list MCP servers | works differently | Catalog omitted `cursor-ide-browser`. |
| detect (id-probe) | `browser_tabs {action:"list"}` by server id | works as documented | Attached. Open tab `about:blank`, `viewId: stable-browser-session/bb3e1486d1f5cb329ccfeb9e2cfe6d01`. Full 16-tool surface then visible. |
| lock | `browser_lock {action:"lock", viewId}` | absent (MCP drop) | `Error: MCP server does not exist: cursor-ide-browser`. |
| recover | id-probe ×4 (`browser_tabs` list / `GetMcpTools`) | absent | Re-probe restored the server **0 times** in this pass. |

## Pass C — dedicated R3 smoke `http://127.0.0.1:8762/` (this repo, same day)

Local page: `console.error('fn-162-deliberate-console-error')` on load + `fetch('/fail')` → HTTP 500. Server verified via curl (`200` / `500`). Rung 4 used by explicit direction.

| Step | Call | Verdict | Actual shape |
|------|------|---------|--------------|
| detect (id-probe) | `GetMcpTools` / `browser_tabs {action:"list"}` | works as documented | Server ready, 16 tools. Tab `about:blank`, `viewId: stable-browser-session/bb3e1486d1f5cb329ccfeb9e2cfe6d01`. |
| lock | `browser_lock {action:"lock", viewId}` | works as documented | `Browser locked.` + `{"locked":true}`. |
| verify (CDP) | `browser_cdp` `Log.enable` + `Network.enable` + `Runtime.enable` (parallel, after lock) | absent (MCP drop) | All three: `MCP server does not exist: cursor-ide-browser`. |
| recover | `browser_tabs {action:"list"}` | works differently | **Restored once.** Same `viewId`. |
| navigate | `browser_navigate {url: http://127.0.0.1:8762/, viewId}` | absent (MCP drop) | Dropped again on the next call. Further list/navigate/GetMcpTools/unlock probes failed. |
| cache dir | `~/.cursor/projects/Users-gordon-work-flow-next/mcps/` | absent | No `cursor-ide-browser/` dir after successful list+lock. |
| release | `browser_lock unlock` | absent | MCP gone. Glass pane **Take Control** if the tab stayed locked. |

The smoke page never loaded in the in-IDE browser. Console/network from the driven surface remain unobserved.

## Inventory vs the old reference

Live 16: `browser_cdp`, `browser_click`, `browser_drag`, `browser_fill`, `browser_get_bounding_box`, `browser_highlight`, `browser_lock`, `browser_mouse_click_xy`, `browser_navigate`, `browser_press_key`, `browser_scroll`, `browser_select_option`, `browser_snapshot`, `browser_tabs`, `browser_take_screenshot`, `browser_type`.

Deleted fiction: `browser_console_messages`. `viewId` is on every tool **except** `browser_tabs` (targets by `index`). `browser_cdp` is real (Cursor-documented), including `Input.*` denied.

## R3 / R6

R3 remains **unresolved**: console + network were not observed from the driven surface, including a dedicated smoke page whose `console.error` + 500 never loaded because the MCP dropped after lock. Do not infer them from CDP method names in `INSTRUCTIONS.md`. A `/flow-next:qa` pass on this rung records an evidence gap, not PASS.

R6 **not taken**: the rung drives (snapshot, screenshot, lock, click/select surface). It was documented wrong; it is not too gapped to route to, provided the evidence-gap caveat rides the ladder row.

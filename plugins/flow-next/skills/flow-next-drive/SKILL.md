---
name: flow-next-drive
description: Drive any UI surface like a real user - a web app, a Chromium-backed desktop app (Electron / WebView2, reached over CDP), or a genuinely native app (macOS AppKit/SwiftUI, or a non-CDP webview) reached via Computer Use. Detects the surface, picks the best available driver, degrades gracefully. Use to navigate sites, verify deployed UI, test web or desktop apps, capture baseline screenshots, drive a sign-in flow, scrape data, fill forms, run an e2e check, or inspect current page state. Triggers on "check the page", "verify UI", "test the site", "test this app", "drive the app", "automate this desktop app", "read docs at", "look up API", "visit URL", "browse", "screenshot", "scrape", "e2e test", "login flow", "capture baseline", "see how it looks", "inspect current", "before redesign", "Electron app", "native app".
---

# flow-next-drive — surface-aware UI automation

Drive any UI surface the way a real user would. Whatever driver the environment has, the work is the same shape: **observe / navigate → snapshot → act on fresh refs → capture evidence → release**. This skill is a *router*: it detects the surface, picks the highest available driver on a ladder, degrades gracefully when a richer driver is absent, and hands off to a per-rung reference for the command detail.

It orchestrates drivers — it does not reimplement them. The default rung (Vercel's `agent-browser` CLI) is the only driver assumed present; every other rung is detected and optional. A pass must succeed with whatever the environment actually has — most cloud VMs, Linux, and CI have no Computer Use, so it is never a hard dependency and never on a headless/no-display path.

> Driver ladder + universal-flow structure adapted from Ray Fernando's `running-bug-review-board` skill (Apache-2.0) — see CHANGELOG.

## Step 1 — Detect the surface, then branch

Classify the target into one of three buckets and take the matching path. The universal flow (Step 2) is shared; only the actuation and the per-surface reference differ.

| # | Surface | What it is | Path |
|---|---------|------------|------|
| A | **Web app** | A URL in a browser (localhost dev server, staging, production) | **Web ladder** (Step 3) |
| B | **Chromium-backed desktop app** | Electron / Windows WebView2 — Chromium under the hood, exposes a CDP debug port | **Web ladder** (Step 3), attaching over CDP to the app's remote-debugging port |
| C | **True-native / non-CDP surface** | macOS AppKit/SwiftUI, Catalyst, or a webview exposing no CDP (macOS WKWebView, which Tauri uses on macOS) | **Native rung** (Step 4) → Computer Use |

How to decide:

- A bare URL, or a dev/staging/prod web app → **A**.
- A desktop app you can launch with `--remote-debugging-port=<n>` (or one already exposing one) → **B**. Electron and Windows WebView2 are Chromium; the web ladder drives them by CDP-attach. Do **not** route these to Computer Use.
- A desktop app with no CDP port — genuinely native (AppKit/SwiftUI), or a macOS WKWebView / Tauri-on-macOS app — → **C**. Per-platform caveat: **Windows WebView2 is CDP-drivable (→ B); macOS WKWebView generally is not (→ C)** — verify per platform.

When unsure whether a desktop app exposes CDP, probe for B first (try to launch/attach with a debug port). If no port is reachable, fall to C.

## Step 2 — The universal flow (all surfaces)

```
observe / list what's open
navigate to the target (URL, or focus the app window)
snapshot              → fresh element refs (REQUIRED before each act)
act                   → click / fill / type / press / scroll toward the next step
verify                → confirm the expected text / state appeared
capture               → screenshot + console/errors at the moment of interest (and on failure)
release               → close the tab / end the session when fully done
```

Refs (`@e1`, `@e2`, …) go **stale** after any navigation, click, or form submit. Always re-snapshot. "Element X has pointer-events: none" or "ref not found" almost always means a stale snapshot, not a real bug — re-snapshot before concluding.

## Step 3 — Web ladder (surfaces A and B)

Probe availability top-down and use the **highest rung that passes**; fail soft to the next; the terminal rung is manual. Never hard-depend on any rung above the default.

| Rung | Driver | Use when | Reference |
|------|--------|----------|-----------|
| 1 (default) | **agent-browser** CLI | Always assumed present. CDP-based, headless-safe, no extra install. Drives web apps; drives Electron / WebView2 over CDP (`--cdp <port>` / `--auto-connect`). | `references/agent-browser.md` |
| 2 | **chrome-devtools-mcp** | You want built-in auto-wait (fewer stale-ref failures), DevTools-grade network/console inspection, Lighthouse, or to **attach to your real signed-in Chrome** (`--browser-url` / `--autoConnect`) so bot defenses don't challenge an automated profile. | `references/chrome-devtools-mcp.md` |
| 3 | **Playwright** (CLI or MCP) | The repo already has Playwright configured, or you need a headless CI-style run / large cross-browser regression suite. | `references/playwright.md` |
| 4 | **cursor-ide-browser** MCP | Running inside Cursor with this MCP installed and you want its snapshot YAML + `browser_cdp` control. | `references/cursor-ide-browser.md` |
| 5 (terminal) | **Manual + screenshot relay** | No browser driver available — drive yourself, paste console errors and screenshots into chat. | — |

**Surface B note:** the SAME ladder drives Electron / WebView2 apps — attach to the app's remote-debugging port (`agent-browser --cdp <port>` / `--auto-connect`; chrome-devtools-mcp `--browser-url=http://127.0.0.1:<port>`). Launch the app with a dedicated debug port and a dedicated user-data-dir; treat the open debug port as a security exposure (any local app can drive that session).

> **agent-browser command detail lives in the rung reference, not here.** The default-rung reference [`references/agent-browser.md`](references/agent-browser.md) is the entry point — setup/version check, the universal flow in agent-browser commands, the Chromium-desktop (Electron / WebView2) CDP driver, the `--headed` daemon-reuse gotcha, and an index into the per-topic references it folds: `commands.md`, `advanced.md` (CDP attach), `auth.md`, `snapshot-refs.md`, `session-management.md`, `proxy.md`, `debugging.md`.

## Step 4 — Native rung (surface C): Computer Use

A genuinely native app (or a non-CDP webview) has no browser tab to attach to. The only way to drive it is **Computer Use** — the model looks at the screen, moves a cursor, clicks, and types. Driver-agnostic across what the host offers: **Codex Computer Use** (macOS/Windows) and/or **Anthropic "Claude" Computer Use** (the API `computer` tool, run via its own harness — a controlled display/sandbox or an MCP wrapper). Detect availability and use whichever the environment provides; verify the tool/beta-header version at build (it drifts).

The actuation differs from the web ladder but the universal flow (Step 2) is identical — `observe → act → verify → capture`, described as goal + success state, not pixel coordinates.

→ Read `references/computer-use.md` for availability detection, the enable/permission walkthrough, the driving loop, safety/hygiene, and the full graceful-degradation table.

## Driver detection & graceful degradation (all surfaces)

1. **Probe, don't assume.** Detect each non-default rung before planning around it (`command -v`, MCP list, `uname -s` for macOS-only Computer Use). Treat anything above the default rung as *probably absent*.
2. **Pick the highest rung that passes; fail soft to the next.** The terminal rung is always manual / documented-limitation — the pass still completes.
3. **Computer Use is never required and never on a headless/CI path.** Most VMs/Linux/CI lack it.
4. **Graceful degradation when no Computer Use is present:**
   - A **Chromium-backed app (B)** still drives via the web-ladder CDP attach (Step 3), or by driving its local dev-server URL in a browser. Note that shell-level integration (system tray, native menus, OS dialogs) can't be reached this way — surface that limitation.
   - A **genuinely native app (C)** with no Computer Use → document the limitation rather than fail.
5. **agent-browser stays the only assumed-present driver.** No MCP server or Computer Use is ever a hard install dependency.

## Boundaries

- **iOS / iPadOS app driving is out of scope** — defer to the community iOS simulator skills. Never spin up an iOS simulator for a web-only app.
- This skill provides driver/actuation + the surface conditional. The full native-desktop QA *workflow* (scenario authoring, bug filing, verdict) is a downstream `/flow-next:qa` concern.
- Don't reinvent what a driver already does (Playwright, Computer Use) — orchestrate, don't replace.

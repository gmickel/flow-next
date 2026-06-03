# agent-browser — default web rung

The default rung of the web ladder (SKILL.md Step 3): Vercel's **agent-browser** CLI. CDP-based, headless by default, no extra install — the only driver assumed present. It drives **web apps (surface A)** and **Chromium-backed desktop apps (surface B — Electron / Windows WebView2)** by attaching over CDP.

This file is the rung's entry point: how to verify the driver, the universal flow expressed in agent-browser commands, the surface-B (Chromium-desktop) driver, the gotchas that bite, and an index into the per-topic references that hold the full command surface.

## Setup & version check (run first)

```bash
# Present + version. Missing → install.
command -v agent-browser >/dev/null 2>&1 && agent-browser --version \
 || echo "MISSING: npm install -g agent-browser (or: brew install agent-browser) then: agent-browser install"
```

- First install also needs the browser binary: `agent-browser install` (add `--with-deps` on Linux for system libs).
- Diagnose a broken install: `agent-browser doctor` (`--fix` auto-cleans stale daemon/lock files).
- agent-browser iterates fast. If the installed version is more than ~a week old, check `npm view agent-browser version` and `agent-browser upgrade`.

**Prefer the installed CLI's own docs over this file when they disagree** — they're always version-matched to the binary you have:

```bash
agent-browser skills get core # overview + common patterns
agent-browser skills get core --full # + full command reference and templates
agent-browser skills list # specialized skills (electron, slack, dogfood, vercel-sandbox, agentcore, ...)
agent-browser --help # flag-level reference
agent-browser <command> --help # per-command help
```

This rung doc captures the flow-next-specific framing and the gotchas; the CLI's `skills get core --full` is the canonical command reference and tracks the installed version.

## The universal flow in agent-browser commands

The SKILL.md universal flow (`observe → navigate → snapshot → act on fresh refs → verify → capture → release`) maps directly:

```bash
agent-browser open https://example.com # navigate
agent-browser wait --load networkidle # let an SPA settle
agent-browser snapshot -i # fresh refs (REQUIRED before each act)
agent-browser click @e1 # act on a ref from THIS snapshot
agent-browser snapshot -i # re-snapshot — refs went stale after the click
agent-browser get text @e5 # verify expected state appeared
agent-browser screenshot out.png # capture evidence (and on failure)
agent-browser close # release when fully done
```

**Re-snapshot after every DOM change.** Refs (`@e1`, `@e2`, …) are invalidated by any navigation, click that changes the page, form submit, or dynamic content load. A "ref not found" or "element has pointer-events: none" is almost always a stale snapshot, not a real bug — re-snapshot before concluding. Full ref model + lifecycle: [snapshot-refs.md](snapshot-refs.md).

### Command chaining (daemon persistence)

The browser persists between commands via a background daemon, so chaining with `&&` in one shell invocation is safe and faster than separate calls:

```bash
# Chain when you don't need intermediate output
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser snapshot -i
```

Run commands separately when you need to parse output first — e.g. `snapshot -i` to discover refs, *then* interact on what you read.

## Surface B — Chromium-desktop driver (Electron / WebView2)

Electron and Windows WebView2 apps are Chromium under the hood, so **agent-browser drives them directly over CDP — this is the Chromium-desktop driver, not merely "connect to Chrome."** No Computer Use needed (see SKILL.md Step 1: route these to the web ladder, not the native rung).

```bash
# Launch the app with a dedicated remote-debugging port + isolated user-data-dir, then:
agent-browser --cdp 9222 snapshot -i # attach by explicit port
agent-browser --cdp 9222 click @e1
agent-browser connect 9222 # equivalent connect command

# Or auto-discover a running Chrome/Chromium exposing a debug port
# (also reuses that profile's signed-in auth state):
agent-browser --auto-connect open https://example.com
agent-browser --auto-connect snapshot -i
agent-browser --auto-connect state save ./auth.json
```

- Use a dedicated debug port **and** a dedicated `--user-data-dir` when launching the app.
- An open debug port is a security exposure — any local process can drive that session. Don't leave it open after the run.
- Shell-level integration (system tray, native menus, OS file dialogs) is *not* reachable over CDP — surface that as a limitation if the scenario needs it.
- Per-platform caveat: **Windows WebView2 is CDP-drivable (stays on this rung); macOS WKWebView (what Tauri uses on macOS) generally is not → route to the native rung (SKILL.md Step 4).**
- The CLI ships a dedicated specialized skill for this: `agent-browser skills get electron` (VS Code, Slack, Discord, Figma, Notion, …).

CDP details + use cases: [advanced.md](advanced.md) ("CDP Mode" — "control Electron apps … WebView2 apps").

## Gotchas

**`--headed` daemon-reuse bug.** If a daemon already started headless, a later `--headed` is ignored (the window won't appear). Kill the daemon first, then relaunch headed:

```bash
agent-browser close
pkill -f "node.*daemon.js.*AGENT_BROWSER"
pkill -f "Google Chrome for Testing"
sleep 1
agent-browser open <url> --headed
```

**"Browser not launched" error** — daemon stuck. Kill and retry:

```bash
pkill -f agent-browser && agent-browser open <url>
```

**Window exists but isn't visible (macOS)** — bring it to the front:

```bash
osascript -e 'tell application "Google Chrome for Testing" to activate'
```

**Slow pages / timeouts.** The default Playwright timeout is 60s. After `open` on a slow site, prefer an explicit `wait --load networkidle` (or `wait "#content"` / `wait --url "**/dashboard"`) over a fixed `wait 5000`.

**Always release.** Close sessions when done to avoid leaked daemon/browser processes: `agent-browser close` (or `agent-browser --session <name> close`; `agent-browser close --all` closes every session). If a prior run wasn't closed cleanly, `agent-browser close` cleans up the stuck daemon.

## Local files

```bash
agent-browser --allow-file-access open file:///path/to/page.html
agent-browser --allow-file-access open file:///path/to/document.pdf
agent-browser screenshot out.png
```

## Configuration file

Persist settings via `agent-browser.json` in the project root:

```json
{ "headed": true, "proxy": "http://localhost:8080", "profile": "./browser-data" }
```

Priority (lowest → highest): `~/.agent-browser/config.json` < `./agent-browser.json` < env vars < CLI flags. Custom path via `--config <path>` or `AGENT_BROWSER_CONFIG`. CLI options map to camelCase keys (`--executable-path` → `"executablePath"`). Full env-var list in [advanced.md](advanced.md).

## Reference index

Every command and flow the agent-browser driver supports lives in these files. Read the one matching your task:

| Topic | File |
|-------|------|
| Full command reference (navigation, interactions, get/state, wait, screenshots, diff, find, set, cookies/storage, network, tabs, frames, dialogs, eval, state, profiling, iOS, global options) | [commands.md](commands.md) |
| Snapshot model, `@ref` lifecycle, re-snapshot rules, annotated screenshots, troubleshooting refs | [snapshot-refs.md](snapshot-refs.md) |
| Auth: state persistence, token/header auth, cookies/storage, OAuth/SSO, 2FA, token refresh, security | [auth.md](auth.md) |
| Sessions: parallel isolated browsers, `--session` / `--session-name`, persistence, encryption, cleanup | [session-management.md](session-management.md) |
| Advanced: network interception/mocking, tabs/windows/frames, dialogs, mouse, settings, **CDP mode (Electron/WebView2)**, eval, extensions, custom executable, env vars | [advanced.md](advanced.md) |
| Proxy: basic/auth/SOCKS proxies, bypass, geo-testing, rotating proxies, corporate networks | [proxy.md](proxy.md) |
| Debugging: headed mode, console/errors, highlight, traces, video recording, profiling, common issues | [debugging.md](debugging.md) |

**iOS / mobile Safari** driving (`agent-browser -p ios …`) is documented in [commands.md](commands.md), but driving iOS apps is out of scope for flow-next-drive (SKILL.md Boundaries) — defer to the community iOS simulator skills.

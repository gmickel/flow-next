# chrome-devtools-mcp — rung 2 (auto-wait + attach-to-real-Chrome)

Web-ladder rung 2 (SKILL.md Step 3). Google's official MCP server, [`ChromeDevTools/chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp). Puppeteer-based with **built-in auto-wait** and DevTools-grade inspection. **Detected, optional** — reach for it over the default rung when you want fewer stale-ref failures, DevTools network/console depth, Lighthouse/performance traces, or to attach to your **real signed-in Chrome** so bot defenses don't challenge an automated profile.

Canonical, version-matched docs (read these over this file when they disagree):

- README + flags: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
- Tool reference: <https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md>
- Troubleshooting (sandbox / root / headless): <https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/troubleshooting.md>
- Remote debugging: <https://developer.chrome.com/docs/devtools/remote-debugging/>

## When this rung wins over agent-browser

- **Auto-wait.** It waits for each action's result before continuing, so the `pointer-events: none` / "ref not found" timing failures mostly disappear — don't hand-roll waits.
- **DevTools depth.** `list_console_messages`, `list_network_requests` / `get_network_request` for 4xx/5xx evidence, `lighthouse_audit`, `performance_start_trace` / `performance_stop_trace`. **The only rung that gives Lighthouse / perf / heap** — escalate here when the task needs them.
- **Attach to real, signed-in Chrome** — sidesteps bot defenses (Cloudflare Turnstile, hCaptcha) that catch a fresh WebDriver profile, and reuses existing auth.

## Install (varies by MCP client — verify at build)

```bash
# Claude Code
claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
# Codex
codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
# Generic MCP config
{ "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"] }
```

## Attach to a RUNNING Chromium app (web + surface B)

Two attach modes. Both reuse the live page state instead of launching a fresh profile.

```bash
# (a) --browser-url: you start Chrome (or the Electron/WebView2 app) yourself,
# then point the MCP at its debug endpoint. Works for sandboxed/VM setups.
chrome --remote-debugging-port=9222 --user-data-dir=/path/to/dedicated-dir
npx chrome-devtools-mcp@latest --browser-url=http://127.0.0.1:9222

# (b) --autoConnect: MCP discovers your already-running Chrome.
# Enable remote debugging at chrome://inspect/#remote-debugging first.
npx chrome-devtools-mcp@latest --autoConnect
```

**`--browser-url` attaches to ANY running Chromium target, not only a fresh Chrome** — point it at an **Electron / Windows WebView2 app** launched with `--remote-debugging-port=<n>` and a dedicated `--user-data-dir`. This is how rung 2 covers Chromium-desktop surfaces (SKILL.md surface B): same web ladder, same `--browser-url` flag, the app's debug port instead of a browser's.

- Use a **dedicated `--user-data-dir`** when you start Chrome/the app for `--browser-url`. The remote-debugging port lets *any* local process drive that session and it carries your real auth — treat the open port as a security exposure and close it after the run.
- `--isolated` — throwaway profile, auto-cleaned on close (use when you don't want to attach to a real session).
- `--headless` — no UI (default `false`). `--channel canary|dev|beta|stable` — pick the Chrome channel.

## Drift-prone facts — **verify at build**

- **`--autoConnect` requires Chrome 144+** and shows an **allow-dialog** (you approve the attach) — confirm both the version floor and the dialog behavior against the current README.
- **Sandbox caveat:** when the MCP client sandboxes the server (macOS Seatbelt, Linux container), **chrome-devtools-mcp cannot launch Chrome** (Chrome needs to create its own sandbox). Workaround: start Chrome yourself outside the sandbox and attach with `--browser-url` (mode (a) above), or disable sandboxing for this server. Running as root also fails Chrome launch (needs `--no-sandbox`); a headless host with no X server needs `xvfb-run` or `--headless`.
- Flag names (`--autoConnect`, `--browser-url`, `--isolated`, `--headless`, `--channel`) and tool names — verify against the installed version's README / `tool-reference.md`; they drift.

## Limits

- **Chrome-only** — no WebKit/Firefox. For cross-browser, drop to the Playwright rung. For a genuinely native (non-CDP) surface, see the native rung (SKILL.md Step 4).
- Emulation is not a real device.

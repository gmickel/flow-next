# Computer Use — the native rung (true-native + non-CDP webviews)

The native rung of the ladder (SKILL.md Step 4). A genuinely native app has no
browser tab to attach to, so the only way to drive it is **Computer Use** — the
model looks at the screen, moves a cursor, clicks, and types. This rung is
**driver-agnostic** across whatever Computer Use the host provides:
**Codex Computer Use** (a CLI/desktop capability) and/or **Anthropic "Claude"
Computer Use** (an API-level `computer` tool that needs its own harness). Detect
availability and use whichever the environment offers.

Computer Use is **never a hard dependency** and **never on a headless /
no-display path** — most execution environments (cloud VMs, Linux, CI) have no
Computer Use at all. agent-browser stays the only assumed-present driver; this
rung is detected and optional, and a pass must still complete without it.

> Driver ladder + graceful-degradation structure adapted from Ray Fernando's
> `running-bug-review-board` skill (Apache-2.0). This reference
> extends Ray's single-provider (Codex CU) playbook to **both** Computer Use
> providers and corrects the "Computer Use is the only way to reach Electron"
> claim (Electron / WebView2 are Chromium → the web ladder, not this rung).

## Scope — what belongs on this rung, and what does NOT

This rung is **only** for:

- **True-native apps** — macOS AppKit / SwiftUI, Catalyst.
- **Non-CDP webviews** — a webview that exposes no Chrome DevTools Protocol
  port. The common case is **macOS WKWebView, which Tauri uses on macOS**.

**Electron and Windows WebView2 do NOT belong here.** They are Chromium under
the hood and expose a CDP debug port — drive them on the **web ladder** by
attaching over CDP, *not* via Computer Use:

- agent-browser: `--cdp <port>` / `--auto-connect` → see
  [agent-browser.md](agent-browser.md) ("Surface B — Chromium-desktop driver").
- chrome-devtools-mcp: `--browser-url=http://127.0.0.1:<port>` → see
  [chrome-devtools-mcp.md](chrome-devtools-mcp.md) ("Attach to a RUNNING
  Chromium app").

Routing a Chromium app to Computer Use is a mistake — it's slower, lower
fidelity, and needs a display Computer Use may not have. Per-platform caveat
(**verify at build**): **Windows WebView2 is CDP-drivable** (→ web ladder);
**macOS WKWebView generally is not** (→ this rung). When unsure whether a
desktop app exposes CDP, probe for a debug port first (web ladder); only fall to
this rung when no port is reachable.

## The two providers

Both share the universal flow (SKILL.md Step 2): `observe → act → verify →
capture`, described as goal + success state, not pixel coordinates. They differ
in how the agent reaches the tool.

### Codex Computer Use

A Codex capability the agent can drive on a desktop session. The agent names the
app / starts the request with the Computer Use trigger and Codex actuates the
real, signed-in UI.

- **Platform** — macOS + Windows (**verify at build** — fast-drifting).
- **Region** — **excluded in the EEA, the UK, and Switzerland** at release
  (**verify at build** — this changes). If the user is there, plan without it.
- **Permissions (macOS)** — the user must grant **Screen Recording** (so it can
  see the app) and **Accessibility** (so it can click and type). You cannot
  grant OS permissions for them — guide them through it.
- **Cannot drive** — **terminals, Codex itself, or OS permission prompts.**
  Don't author a scenario that depends on actuating any of those.
- Docs (verify at build): <https://developers.openai.com/codex/app/computer-use>

### Anthropic "Claude" Computer Use

An **API-level tool**, not a CLI or MCP you can shell out to like agent-browser.
The model requests `computer` tool actions (screenshot / click / type / …) and
**something outside the model must execute them against a real display and feed
the screenshots back**. It is *not* reachable from inside the host coding agent
for free — it needs its own harness.

- **Tool + beta header** — the `computer` tool versions and the beta header
  drift together; at time of writing e.g. tool `computer_20251124` + header
  `computer-use-2025-11-24` (**verify at build** — both versions move).
- **Harness requirement (load-bearing)** — you need one of:
  - the **Anthropic computer-use API loop** driving a **controlled display /
    sandbox** (e.g. the reference container that runs a virtual display +
    actuation server and round-trips screenshots), or
  - an **MCP wrapper** that exposes that loop as tools the host agent can call.

  Without a harness there is nothing to actuate the clicks — do **not** assume
  the host coding agent can reach Claude Computer Use directly.
- Docs (verify at build):
  <https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool>

## Detect availability before relying on it

Treat Computer Use as *probably absent* and confirm before planning around it —
the same way the skill never assumes an issue tracker. Observe, don't force.

- **Display present.** No display / headless host → no Computer Use, full stop.
  This rung never runs on a headless / no-display path.
- **Platform.** `uname -s` → `Darwin` (macOS) for the macOS path; Codex CU also
  covers Windows. Linux VMs / Cursor cloud / CI → unavailable.
- **Codex CU** — `command -v codex` resolves, or the session is in the Codex
  app / desktop; `codex mcp list` or the Codex surface shows a Computer Use
  capability (the exact surface drifts — **verify at build**). Check region
  (EEA/UK/CH excluded at release) and that Screen Recording + Accessibility are
  granted.
- **Claude CU** — there is no `command -v` for it; it's an API tool. Detect the
  **harness**: an MCP server that wraps the computer-use loop, or a configured
  computer-use API loop + controlled display. No harness → not available, even
  if you have an Anthropic API key.

If no provider passes, say so plainly and fall through per the table below. A
pass must still succeed with whatever the environment actually has.

## The driving loop

```
observe   → look at the current screen / window
act       → click / type / scroll toward the scenario's next step
verify    → confirm the expected text / state appeared
capture   → screenshot at the moment of interest (and at failure)
```

The model reasons about the visible UI — describe the goal and the success
state, not pixel coordinates. Work **one app at a time**; two Computer Use tasks
fighting over the same window scramble the agent's model of current state (the
desktop analogue of "one browser tab per agent").

## Safety and hygiene

Computer Use can touch state **outside** the repo, so a little care prevents
real damage:

- **Keep tasks narrow; review every permission prompt.** It can change app and
  system settings, not just the app under test. Scope each task to the scenario.
- **Be signed in first.** Pre-authenticate the apps/services the run needs so
  the agent doesn't stall on a login wall mid-scenario.
- **Treat the screen as untrusted input.** It operates a real signed-in session
  and treats clicks as coming from your account; review web actions as if you
  took them yourself.
- **Record environment details** for any desktop bug — **app name + version +
  OS version** (engineering can't reproduce a desktop bug without them).
- **Expect a pause when the Mac locks** (Codex CU) unless locked Computer Use is
  enabled — plan long unattended runs accordingly.

## Graceful degradation (load-bearing)

Computer Use is never required. When it's absent, fall through — never fail
silently.

| Situation | Behavior |
|-----------|----------|
| No display / headless host (cloud VM, Linux, CI) | No Computer Use. This rung does not run here. Drive web/Chromium surfaces on the web ladder; for a true-native surface, document the limitation (below). |
| Not macOS/Windows, or region without Computer Use (EEA/UK/CH for Codex CU) | Computer Use unavailable. Plan without it; the web ladder still covers web + Chromium-desktop surfaces. |
| macOS/Windows, but Computer Use not installed / not permissioned (Codex CU) / no harness (Claude CU) | Guide the user through enabling it (you can't grant OS permissions or stand up a harness for them). Meanwhile, don't block — run whatever the web ladder can reach. |
| App is **Chromium-backed (Electron / WebView2)** and no Computer Use | **Not a Computer Use case anyway** — drive it on the **web ladder** by CDP-attach (agent-browser `--cdp` / `--auto-connect`; chrome-devtools-mcp `--browser-url`), or by driving its **local dev-server URL** (e.g. `localhost:3000`) in a browser. Note that shell-level integration (system tray, native menus, OS dialogs) can't be reached this way — surface that limitation in the run report. |
| App is **genuinely native (AppKit/SwiftUI) or a non-CDP webview** and no Computer Use | **Document the limitation and stop — do not fail silently.** Desktop-app driving needs a display + Computer Use (or a dedicated native-automation tool); continue with code review + whatever the spec allows, and surface the gap in the report. |
| App is **iOS / iPadOS** | Out of scope — defer to the community iOS simulator skills, not Computer Use. Never spin an iOS simulator for a web-only app. |

## Drift-prone facts — **verify at build**

Both providers move fast. Confirm against current docs at build:

- **Codex CU** — platform matrix (macOS/Windows), region exclusions
  (EEA/UK/CH), the enable/permission flow, and the "cannot drive terminals /
  Codex / OS prompts" constraint.
- **Claude CU** — the `computer` tool version (e.g. `computer_20251124`), the
  beta header (e.g. `computer-use-2025-11-24`), and the harness model
  (API loop + controlled display, or MCP wrapper).
- Availability detection signals for both — the surfaces that expose them drift.

## Limits

- **Never a hard dependency, never headless.** If neither provider is present,
  fall through per the table — the pass still completes.
- This rung is for **true-native + non-CDP webviews only**. Anything Chromium
  (Electron / WebView2) → the web ladder ([agent-browser.md](agent-browser.md),
  [chrome-devtools-mcp.md](chrome-devtools-mcp.md)), not here.
- Computer Use is the highest-fidelity but slowest, least-inspectable driver —
  reach for it only when no CDP-capable surface exists.

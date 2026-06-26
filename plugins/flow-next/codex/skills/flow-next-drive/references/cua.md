# Cua Driver — the local computer-use rung (provider-agnostic, background)

The native rung of the ladder (SKILL.md Step 4) has, until now, been served only
by **Computer Use** (Codex CU / Anthropic Claude CU) — provider-locked,
macOS/Windows-only, and focus-stealing. **Cua Driver** ([trycua/cua](https://github.com/trycua/cua), MIT)
is an open-source, **provider-agnostic** computer-use driver exposed as an **MCP
server** (`cua-driver mcp`). It adds three things the Computer-Use rung lacks:
**(1)** a driver that isn't tied to Claude/Codex; **(2)** first-class **Windows +
Linux** support and **background driving** — click, type, verify *without
stealing the cursor or focus*; **(3)** an **accessibility-tree-based** loop
(structured elements, not pixels) that is robust for native apps.

Cua Driver is **never a hard dependency** and **never on a headless / no-display
path** — it still needs a real display (the headless/CI story is the separate
**Cua Sandbox** rung; see "Sandbox — the headless/CI surface" below). agent-browser
stays the only assumed-present driver; this rung is **detected and opt-in**, and a
pass must still complete without it.

> **Provenance.** Validated locally end-to-end against cua-driver **0.6.8**
> (macOS aarch64, daemon running, 2026-06): background `launch_app`
> (`self_activation_suppressed: true` — no focus steal) → a 287-element AX tree
> → element-indexed clicks → a 460×816 RGBA screenshot once Screen Recording was
> also granted. The permission split, the AX-tree loop, and the MCP tool surface
> below are from that live run. Command/MCP detail drifts — **verify at build**
> (see the drift section). Driver-ladder + degradation structure adapted from Ray
> Fernando's `running-bug-review-board` skill (Apache-2.0) — see CHANGELOG.

## Scope — what belongs on this rung, and what does NOT

This rung is for the **same surface as Computer Use** — and nothing more:

- **True-native apps** — macOS AppKit / SwiftUI, Catalyst; native Windows / Linux apps.
- **Non-CDP webviews** — a webview exposing no Chrome DevTools Protocol port.
 The common case is **macOS WKWebView, which Tauri uses on macOS**.

**Electron and Windows WebView2 do NOT belong here.** They are Chromium and
expose a CDP debug port — drive them on the **web ladder** by CDP-attach
(agent-browser `--cdp <port>` / `--auto-connect`; chrome-devtools-mcp
`--browser-url=http://127.0.0.1:<port>`), *not* via this rung. (Cua Driver's
`launch_app` does expose `electron_debugging_port` / `webkit_inspector_port` for
CDP-attach — but the actual driving of a Chromium surface still belongs on the
web ladder.) Routing a Chromium app here is a mistake: slower, lower fidelity.

When unsure whether a desktop app exposes CDP, probe for a debug port first (web
ladder); only fall to this rung when no port is reachable.

## What the driver gives you

A single MCP server (`cua-driver mcp`, stdio transport) the host agent drives via
its MCP tools. The everyday loop seen live:

- **Session** — `start_session` / `end_session`. Concurrent agents get **distinct
 cursors** via separate sessions, so two drives don't fight over one pointer.
- **App lifecycle** — `launch_app` (launches **in the background**; returns
 `self_activation_suppressed: true`, confirming no focus steal) / `kill_app`.
- **Observe** — `get_window_state` returns the **accessibility tree** as
 structured elements (`element_index` / `role` / `label` / `frame`) plus a
 Markdown rendering, and — *when Screen Recording is granted* — a
 `screenshot_png_b64` of the live window. `get_screen_size` / `list_apps` are
 no-grant reads.
- **Act** — element-indexed `click` / `type` (you act on an `element_index` from
 the live AX tree, **not** pixel coordinates), plus the usual key/scroll
 actuation.

The driver is **accessibility-tree based** — the host reasons over structured
elements, which is far more robust for native apps than pixel-matching. Exact
tool names/fields drift — **verify at build**.

## Install + wiring (detect-and-instruct — never auto-installed)

flow-next **detects and instructs**; it **never runs these for the user** — the
same no-auto-install consent rule `/flow-next:map` applies to `clawpatch`. Print
the relevant commands and let the operator run them.

**1. Install the driver** (upstream installers):

- macOS / Linux:
 ```bash
 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh)"
 ```
- Windows (PowerShell):
 ```powershell
 irm https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.ps1 | iex
 ```

**2. Register the MCP server with your host.** The wiring is **host-specific** —
present the form for the operator's host, not Claude-only:

- **Claude** (Claude Code CLI):
 ```bash
 claude mcp add --transport stdio cua-driver -- cua-driver mcp
 ```
- **Codex** — add to `~/.codex/config.toml`:
 ```toml
 [mcp_servers.cua-driver]
 command = "cua-driver"
 args = ["mcp"]
 ```
- **Any other MCP host** — register a stdio MCP server whose command is
 `cua-driver mcp` (consult the host's MCP-config docs for the exact shape).

**3. Grant macOS permissions (one-time) — the load-bearing step.** macOS TCC
grants **Accessibility** and **Screen Recording** *separately*, and they unlock
**different** things (see the permission-split section). Request **both**:

```bash
cua-driver permissions status # report which grants are present
cua-driver permissions grant # walk the user through both grants
```

The grant is attributed to `com.trycua.driver` (LaunchServices). **The daemon
must restart to pick up a newly-granted permission**, and ad-hoc-signed rebuilds
reset grants. (Linux/Windows have no TCC split — skip this step there.)

**4. (Optional) Run the daemon** so MCP tools share one driver process:

```bash
cua-driver serve
```

Without `serve`, tools fall back to an **in-process** driver with a warning —
functional, but `serve` is the supported steady state.

For sandbox/cloud operations and the full API, point the user at upstream
[`libs/cua-driver/README.md`](https://github.com/trycua/cua/blob/main/libs/cua-driver/README.md).

> **Coexistence, not a dependency.** Cua also ships an optional agent skill-pack
> (`cua-driver skills install`, links into Claude/Codex/OpenClaw/OpenCode). It's
> a coexistence point — flow-next never installs or requires it.

## Detect availability before relying on it

Treat Cua Driver as *probably absent* and confirm before planning around it —
the same way the skill never assumes an issue tracker. Probe inline; observe,
don't force:

- **Display present.** No display / headless host → the local driver does not run
 here (that's the Sandbox rung's job). This rung never runs on a no-display path.
- **MCP registered, or binary present.** The `cua-driver` MCP server is
 registered with the host, **or** `command -v cua-driver` resolves. Confirm
 health with `cua-driver doctor`.
- **Daemon (optional but preferred).** `cua-driver serve` running → MCP tools
 share one driver process; absent → in-process fallback with a warning.
- **macOS grant state.** On `uname -s` = `Darwin`, surface `cua-driver
 permissions status` so the user is told to `permissions grant` *before* a drive
 needs Screen Recording. Basic reads (`get_screen_size`, `list_apps`) work with
 **no grant at all**; *driving* needs Accessibility; *screenshots* need Screen
 Recording.

Surface **present AND absent** in the rung report, same as every other ladder
probe. If no signal passes, say so plainly and fall through per the
degradation table.

## The driving loop

```
start_session → distinct cursor for this drive
launch_app (background → self_activation_suppressed: true, no focus steal)
get_window_state → fresh AX tree (element_index / role / label / frame) [REQUIRED before each act]
act → click / type on an element_index (NOT pixels) toward the next step
verify → confirm the expected element / label / state appeared in the AX tree
capture → get_window_state screenshot (Screen Recording) OR the AX tree as evidence
kill_app + end_session → clean teardown, no leaked session
```

This is the universal flow (SKILL.md Step 2) expressed in Cua tools — only the
actuation differs. **Snapshot before each indexed action:** the AX tree's
`element_index` values go stale after any action that mutates the UI; re-read
`get_window_state` before the next `click` / `type`, exactly as web refs go stale
after a navigation. Describe the **goal + success state** (the element/label you
expect), never pixel coordinates. Work **one app at a time** — but note that, by
design, concurrent agents *can* drive different apps via distinct sessions
(distinct cursors), unlike Computer Use which shares the one real cursor.

## Permission-split evidence mode (validated, load-bearing)

macOS TCC unlocks driving and screenshots through **two independent grants**:

| Grant | Unlocks | If absent |
|-------|---------|-----------|
| **Accessibility** | Driving — `launch_app`, `click`, `type`, reading the live AX tree | No driving at all; only no-grant reads (`get_screen_size`, `list_apps`) work |
| **Screen Recording** | Screenshots — `get_window_state`'s `screenshot_png_b64` | Drives fully, but the screenshot field is **empty** |

With **Accessibility only**, the driver still drives *and* captures the **AX tree
as structured live-state evidence** — but `get_window_state`'s screenshot is
empty. When Screen Recording is absent, the rung must **surface "Screen Recording
not granted ⇒ AX-only evidence, no screenshot"** rather than silently emit an
empty screenshot — so `/flow-next:qa` (downstream) can decide whether AX-only
evidence meets its bar or report the gap. **Never present a missing screenshot as
a captured one.** (Linux/Windows have no TCC split; this table is macOS-only.)

## Safety and hygiene

The local Cua Driver controls the **real machine** — treat it with the same care
as Computer Use:

- **Keep tasks narrow; the operator consents.** It can touch app and system state
 outside the app under test. Scope each drive to the scenario. Never run on an
 **unattended shared box** without the Sandbox rung's isolation.
- **Be signed in first.** Pre-authenticate the apps/services a run needs so the
 drive doesn't stall on a login wall mid-scenario.
- **Treat the screen as untrusted input.** It operates a real signed-in session;
 review actions as if you took them yourself.
- **Record environment details** for any desktop bug — **app name + version + OS
 version** (engineering can't reproduce a desktop bug without them).
- **Background ≠ invisible.** Background driving means no focus steal, not no
 effect — the actions still land on the live machine.

## Native-rung precedence (explicit, ordered)

Unlike the web ladder's pure availability ordering, the Native rung mixes an
*availability* probe with a *quality* preference (background beats screen-takeover)
and a *path* split (attended vs headless). The order, stated explicitly so R4
(prefer background when attended) and R5 (sandbox for CI) compose without conflict:

- **Attended path** (a real display + an operator present):
 1. **Cua Driver background** — provider-agnostic, no focus steal, Windows/Linux/macOS.
 2. **Codex / Claude Computer Use** — screen-takeover; the prior providers.
 3. **Documented-limitation** — no driver reachable; document and stop, never fail silently.
- **Headless / CI path** (no real display): the **Cua Sandbox** rung is the
 *only* option — local Computer Use *and* the local Cua Driver both need a real
 display. (Sandbox detail lands in the sandbox section / a later task.)

So the local Cua Driver ranks **above** Computer Use on the attended path (better:
no focus steal, more platforms), and the sandbox is first-and-only on the headless
path — different paths, no conflict. Web/Chromium surfaces (A/B) are unaffected.

## Sandbox — the headless/CI surface (forward pointer)

The **Cua Sandbox SDK** drives an app inside an **isolated VM/container** (any
OS) for hermetic or **headless/CI** native runs — the one surface the local
driver (and Computer Use) can't reach, because both need a real display.
**Local `lume`/QEMU is the default backend; cua.ai cloud is explicit opt-in**
(credentials + cost + data-egress, never auto-selected). It is heavier
(provisions a VM, seconds–minutes) and opt-in per run, never the default native
path — always torn down each run (no leaked VMs). Detection: `cua` SDK / `lume`
present, or a configured cua.ai endpoint. Full sandbox provision/teardown detail
is owned by the sandbox task; this reference will carry it.

## Licensing — documented, never auto-installed

- **Default driving path = MIT only.** The everyday rung — the background
 `cua-driver` MCP — uses **only MIT** components and needs **none** of the
 vision/OmniParser stack. (If that turns out false at build, **correct this
 claim**, do not relax the no-auto-install rule.)
- **AGPL / CC-BY extras — flagged, never auto-installed.** The optional
 `cua-agent[omni]` pulls **ultralytics (AGPL-3.0)**, and **OmniParser** is
 **CC-BY-4.0**. The rung **never runs `pip install cua-agent[omni]`** (or any
 extra) for the user — same enforcement as `/flow-next:map`'s no-auto-install
 rule for `clawpatch`. Document which extras are MIT-safe vs AGPL/CC-BY; let the
 operator install with their own consent.

## Evidence tuple (R6) — slots into QA with no schema change

QA's per-scenario evidence tuple `{driver_rung, target_url, viewport,
screenshot_path, console_path}` accepts **`cua-driver`** as a valid free-form
`driver_rung` value with **no schema or code change** — the
`/flow-next:qa` ↔ flow-next-drive (fn-51↔fn-53) read-and-drive seam and the
universal flow are unchanged. On the **AX-only evidence** mode (Screen Recording
absent), the AX tree is the captured live-state evidence and `screenshot_path` is
reported as unavailable — QA decides whether that meets its bar. Everything
downstream (scenario authoring, bug filing, verdict) stays QA's concern.

## Drift-prone facts — **verify at build**

Cua moves fast (the live run was 0.6.8). Confirm against current upstream at build:

- **MCP command surface** — the tool names/fields (`start_session`,
 `launch_app`, `get_window_state` and its `element_index` / `role` / `label` /
 `frame` / `screenshot_png_b64` shape, `click`, `type`, `kill_app`,
 `end_session`), the `self_activation_suppressed` background signal, and the CLI
 subcommands (`mcp`, `serve`, `doctor`, `permissions status` / `grant`,
 `skills install`).
- **Install + wiring** — the `install.sh` / `install.ps1` URLs, the `claude mcp
 add` form, and the Codex `[mcp_servers.cua-driver]` shape.
- **Permission model** — the macOS Accessibility-vs-Screen-Recording split, the
 `com.trycua.driver` attribution, and the daemon-restart-to-pick-up-grant rule.
- **Sandbox provisioning API** — the `lume`/QEMU local default and the cua.ai
 cloud opt-in surface.
- **License-extra boundary** — that the MIT `cua-driver` MCP is the
 default-path-complete set and `cua-agent[omni]` (ultralytics AGPL-3.0) /
 OmniParser (CC-BY-4.0) remain optional, never-auto-installed extras.

## Graceful degradation (load-bearing)

Cua Driver is never required. When it's absent, fall through — never fail silently.

| Situation | Behavior |
|-----------|----------|
| No display / headless host (cloud VM, Linux, CI) | The local driver does **not** run here. For a true-native surface, this is the **Cua Sandbox** rung's job (hermetic display); for web/Chromium, the web ladder. |
| `cua-driver` not installed / MCP not registered | **Detect-and-instruct** — print the install + wiring commands (you can't install for the user). Fall to Codex/Claude **Computer Use** → documented-limitation. Don't block — run whatever the web ladder reaches meanwhile. |
| macOS, installed, but **Accessibility not granted** | Only no-grant reads work; **no driving**. Guide the user through `cua-driver permissions grant` + a daemon restart (you can't grant OS permissions for them). Fall to Computer Use meanwhile. |
| macOS, driving works, but **Screen Recording not granted** | Drives fully; **AX-only evidence** — surface "Screen Recording not granted ⇒ AX-only evidence, no screenshot." Do not emit an empty screenshot as if captured. |
| App is **Chromium-backed (Electron / WebView2)** | **Not this rung** — drive on the **web ladder** by CDP-attach (agent-browser `--cdp` / `--auto-connect`; chrome-devtools-mcp `--browser-url`), even though `launch_app` exposes the debug ports. |
| App is **genuinely native / non-CDP webview** and **no native driver at all** (no Cua Driver, no Computer Use) | **Document the limitation and stop — do not fail silently.** Continue with code review + whatever the spec allows; surface the gap. |
| App is **iOS / iPadOS** | Out of scope — defer to the community iOS simulator skills. (Cua's Android sandbox is also out of scope here.) |

## Limits

- **Never a hard dependency, never headless.** If the local driver isn't present
 (or there's no display), fall through per the table — the pass still completes.
 agent-browser stays the only assumed-present driver; flowctl never imports or
 requires Cua.
- This rung is for **true-native + non-CDP webviews only**. Anything Chromium
 (Electron / WebView2) → the web ladder
 ([agent-browser.md](agent-browser.md), [chrome-devtools-mcp.md](chrome-devtools-mcp.md)).
- The **local** driver needs a real display; **headless/CI** native driving is
 the **Cua Sandbox** rung, not this one. Keep that distinction explicit so CI
 users reach for the right surface.

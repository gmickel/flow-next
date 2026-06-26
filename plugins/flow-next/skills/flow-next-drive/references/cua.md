# Cua Driver — the local computer-use rung (provider-agnostic, background)

The native rung of the ladder (SKILL.md Step 4) has, until now, been served only
by **Computer Use** (Codex CU / Anthropic Claude CU) — provider-locked,
macOS/Windows-only, and focus-stealing. **Cua Driver** ([trycua/cua](https://github.com/trycua/cua), MIT)
is an open-source, **provider-agnostic** computer-use driver exposed as an **MCP
server** (`cua-driver mcp`). It adds three things the Computer-Use rung lacks:
**(1)** a driver that isn't tied to Claude/Codex; **(2)** first-class **Windows**
support (**Linux is pre-release/experimental** — Wayland-only limits, not yet a
fully-tested tier; treat it as experimental and fall to the sandbox or
documented-limitation rung) plus **background driving** — click, type text,
verify *without stealing the cursor or focus*; **(3)** an **accessibility-tree-based** loop
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
  **Platform scope (0.6.8):** `launch_app` / `list_apps` / `list_windows` are
  **macOS-shaped** — `launch_app` takes a macOS `bundle_id` (e.g.
  `com.apple.calculator`) + `open -n`; `list_windows` reads the macOS WindowServer.
  On **Windows / Linux** native runs, do **not** assume `launch_app` works the same
  — the target is typically **already running** (discover + attach by `pid` rather
  than cold-launch), and the cold-launch/focus path is platform-specific. **Verify
  the Windows/Linux launch surface at build** (the driver's Windows tier is
  pre-release; see "drift / verify-at-build").
- **Observe** — `get_window_state` returns the **accessibility tree** as
  structured elements (`element_index` / `role` / `label` / `frame`) plus a
  Markdown rendering, and — *when Screen Recording is granted* — a
  `screenshot_png_b64` of the live window. `get_screen_size` / `list_apps` are
  no-grant reads.
- **Act** — element-indexed `click` / `type_text` (you act on an `element_index`
  from the live AX tree, **not** pixel coordinates), plus `press_key` / `hotkey`
  / `scroll` actuation. *(The MCP text-entry tool is `type_text`, not `type` —
  per `cua-driver list-tools`; a bare `type` call will not resolve.)*

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

> **Supply-chain note.** These are upstream's official installers, piped from the
> **mutable `main` branch** — a compromised upstream could turn `curl … | bash` /
> `irm … | iex` into arbitrary code execution. For sensitive or CI machines,
> review the script first (drop the pipe and inspect) or pin a release tag instead
> of `main`. flow-next only *instructs*; it never runs these for you.

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
cua-driver permissions status   # report which grants are present
cua-driver permissions grant    # walk the user through both grants
```

The grant is attributed to `com.trycua.driver` (LaunchServices). **The daemon
must restart to pick up a newly-granted permission**, and ad-hoc-signed rebuilds
reset grants. (Linux/Windows have no TCC split — skip this step there.)

**4. (Optional) Run the daemon** so MCP tools share one driver process:

```bash
cua-driver serve   # macOS / Linux, and Windows from an interactive desktop session
```

Without `serve`, tools fall back to an **in-process** driver with a warning —
functional, but `serve` is the supported steady state.

> **Windows from SSH / a non-interactive shell:** a bare `cua-driver serve` lands
> in **Session 0**, where the GUI tools return empty arrays (installed but
> undriveable). Use the autostart path instead — it runs the daemon in the user's
> **interactive** session:
> ```powershell
> cua-driver autostart enable   # register a logon Scheduled Task
> cua-driver autostart kick     # start it now without re-logging in
> ```

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
start_session         → distinct cursor for this drive
launch_app (background → self_activation_suppressed: true, no focus steal)
get_window_state      → fresh AX tree (element_index / role / label / frame)  [REQUIRED before each act]
act                   → click / type_text on an element_index (NOT pixels) toward the next step
verify                → confirm the expected element / label / state appeared in the AX tree
capture               → get_window_state screenshot (Screen Recording) OR the AX tree as evidence
kill_app + end_session → clean teardown, no leaked session
```

This is the universal flow (SKILL.md Step 2) expressed in Cua tools — only the
actuation differs. **Snapshot before each indexed action:** the AX tree's
`element_index` values go stale after any action that mutates the UI; re-read
`get_window_state` before the next `click` / `type_text`, exactly as web refs go stale
after a navigation. Describe the **goal + success state** (the element/label you
expect), never pixel coordinates. Work **one app at a time** — but note that, by
design, concurrent agents *can* drive different apps via distinct sessions
(distinct cursors), unlike Computer Use which shares the one real cursor.

## Permission-split evidence mode (validated, load-bearing)

macOS TCC unlocks driving and screenshots through **two independent grants**:

| Grant | Unlocks | If absent |
|-------|---------|-----------|
| **Accessibility** | Driving — `launch_app`, `click`, `type_text`, reading the live AX tree | No driving at all; only no-grant reads (`get_screen_size`, `list_apps`) work |
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
  1. **Cua Driver background** — provider-agnostic, no focus steal, macOS/Windows (Linux pre-release/experimental — fall to sandbox/limitation there).
  2. **Codex / Claude Computer Use** — screen-takeover; the prior providers.
  3. **Documented-limitation** — no driver reachable; document and stop, never fail silently.
- **Headless / CI path** (no real display): the **Cua Sandbox** rung is the
  *only* option — local Computer Use *and* the local Cua Driver both need a real
  display. (Full detail in "Sandbox — the headless/CI surface" below.)

So the local Cua Driver ranks **above** Computer Use on the attended path (better:
no focus steal, more platforms), and the sandbox is first-and-only on the headless
path — different paths, no conflict. Web/Chromium surfaces (A/B) are unaffected.

## Determining headless / CI (which path you're on)

The split above hinges on one question — **is a usable display reachable?**
Determine it, never assume — and keep it **separate from driver-install state and
TCC grants** (different questions, see the cautions below). In order:

1. **CI short-circuit.** `$CI` set (GitHub Actions, GitLab CI, CircleCI, etc. all
   export it) ⇒ treat as headless: skip the attended, focus-stealing local driver
   and go straight to the **Cua Sandbox** rung.
2. **Probe only when the driver is installed.** The display probe is meaningful
   *only* if `cua-driver` actually exists. **A probe that fails because the binary
   is absent is NOT a no-display signal** — never route an attended machine to the
   sandbox just because nothing is installed.

   - **Driver present** (`command -v cua-driver`): `cua-driver call get_screen_size`
     returns positive dims when a real display is reachable. The CLI returns a flat
     `{width, height, scale_factor}` (verified 0.6.8); tolerate the MCP
     `structuredContent` envelope too:

     ```bash
     if ! command -v cua-driver >/dev/null 2>&1; then
       DISPLAY_PRESENT=unknown   # driver absent — can't probe; fall back to env/platform (#3) + Computer Use, NOT headless
     elif cua-driver call get_screen_size 2>/dev/null \
          | jq -e '(.width // .structuredContent.width // 0) > 0
                   and (.height // .structuredContent.height // 0) > 0' >/dev/null; then
       DISPLAY_PRESENT=1         # display reachable (positive WIDTH and HEIGHT) → attended ladder
     else
       DISPLAY_PRESENT=0         # driver present but no display → headless (Cua Sandbox if a backend exists)
     fi
     ```

   - **Driver absent:** you can't probe — do **not** infer headless. Fall back to
     env/platform (#3) and let the **Computer Use** ladder (and its own display
     check) decide; only a real no-display signal routes to the sandbox.
3. **Env/platform fallback (driver absent).** On **Linux**,
   `[ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]` is a fast headless hint.
   **Never use `$DISPLAY` on macOS** — it's unset on a fully-displayed Mac (verified:
   a 5120×1440 Mac reports `$DISPLAY` unset), so it false-positives headless. macOS
   always has a window server even over SSH; absent the driver, assume **attended**
   and let Computer Use's own probe decide.

**Two things that are NOT a headless signal (don't conflate them):**

- **TCC grants (macOS).** `get_screen_size` works with **no** grants. Missing
  **Accessibility** is an *attended-path driver failure* → fall through to Computer
  Use, **not** the sandbox. Missing **Screen Recording** still drives (AX-only
  evidence). Keep grant state out of the display decision entirely.
- **Driver not installed.** That's a *detect-and-instruct* gap (print the install),
  not proof of no display — see #2.

`cua-driver doctor` reports install / TCC health, **not** display presence — don't
use it for this decision.

## Sandbox — the headless/CI surface

The **Cua Sandbox SDK** drives an app inside an **isolated VM/container** (any
OS) for hermetic or **headless/CI** native runs — the one surface the local Cua
Driver (and Computer Use) can't reach, because both need a real display. A
sandbox is a **full, disposable computer**: it starts from a known image,
accumulates state only while it lives, and is deleted without consequence — so a
native-app QA pass can finally run **unattended / in CI**, on a host with no
screen of its own.

This is a **less-grounded surface than the local driver**: the local Cua Driver
was validated live end-to-end (see the Provenance note up top), **the Sandbox SDK
was not**. Treat every provisioning / image / SDK-shape claim below as
**verify at build** unless you record an actual provisioning run — the API moves
fast (the SDK surface here is from the upstream docs at authoring time, not a
live run).

### When the sandbox is the rung — and when it is not

The sandbox is the **headless / CI-only** rung. Reach for it when there is **no
real display** (cloud VM, Linux CI runner, an unattended box) and the surface is
genuinely native — that is the *only* place it wins outright, because local
Computer Use and the local Cua Driver both simply cannot run there.

On an **attended path** (a real display + an operator present) the sandbox ranks
**below** the local Cua Driver and below Computer Use purely on **cost and
latency** — provisioning a VM costs seconds-to-minutes and disk where a local
background drive is near-instant. So it does **not** displace the attended
ordering in "Native-rung precedence" above; it slots in as the headless leg. The
two compose:

- **Attended path:** Cua Driver background → Computer Use → documented-limitation
  (the sandbox is available but not preferred — only worth it for hermetic
  isolation the operator explicitly wants).
- **Headless / CI path:** **Cua Sandbox only** — first and last resort, because
  nothing else can drive a native surface with no display.

Still **for true-native + non-CDP surfaces only** (same scope rule as the rest of
this rung). A Chromium app (Electron / WebView2) in CI belongs on the web ladder
(headless agent-browser), not in a provisioned desktop VM.

### Two backends — local default, cloud explicit opt-in

The Sandbox rung has two backends with **very different** privacy/cost profiles.
**Never auto-select the cloud.**

| Backend | What it is | Default? | Cost / privacy |
|---------|-----------|----------|----------------|
| **Local** (`lume` / QEMU / Docker) | A VM/container on the operator's own hardware — no driven data leaves the machine (**set `CUA_TELEMETRY_ENABLED=false` for fully-offline; the SDK ships usage telemetry on by default**) | **Yes — the default sandbox path** | Free; uses local CPU/RAM/disk. Consistent with flow-next's no-SaaS posture. |
| **Cloud** (`cua.ai`) | A managed VM on Cua's infrastructure, same SDK surface | **No — explicit opt-in only** | **Bills**, and **the driven screen + data leave the machine** (data egress). Requires a `CUA_API_KEY`. |

The local backend matrix (verify at build): **Linux** → Docker container (shares
the host kernel, fast to start); **macOS** → a VM via **Lume** (Apple
Virtualization Framework); **Windows** → QEMU / Hyper-V; **Android** → QEMU
(Android is out of scope for this rung regardless). Containers start in seconds;
full VMs are slower but higher-fidelity.

**The cloud backend is opt-in per run and never the inferred default.** It
*receives the driven screen* — that is real data egress — and it bills. Document
the credential (`CUA_API_KEY` from the cua.ai Dashboard → API Keys), the cost,
and the egress at the point of use; require an explicit operator choice. The
zero-network **local** backend is what the rung reaches for unless the operator
asks for the cloud by name.

### Detect availability before relying on it

Same posture as the local driver — *probably absent*, confirm before planning
around it. Probe inline; observe, don't force:

- **Local backend present.** The `cua` Python SDK is importable **and** a local
  VM/container backend is usable: `command -v lume` (macOS VM), `command -v
  docker` + a running daemon (Linux container), or a QEMU install. No backend →
  no local sandbox.
- **Cloud backend configured.** `CUA_API_KEY` is set **and** the operator has
  opted into the cloud for this run. Never treat a present key as consent to
  egress — the cloud is opt-in per run.
- **Headless is fine here.** Unlike every other native rung, the sandbox is
  *designed* for a no-display host — that is its whole point. Absence of a
  display is **not** a degradation signal for this rung.

Surface **present AND absent** in the rung report, same as every other ladder
probe. Absent local backend *and* no opted-in cloud → no sandbox rung; on a
headless host that means the native surface is undriveable → documented
limitation (don't fail silently).

### Install + wiring (detect-and-instruct — never auto-installed)

flow-next **detects and instructs**; it **never runs these for the user** —
the same no-auto-install consent rule the local driver follows (and `/flow-next:map`
follows for `clawpatch`). Print the relevant commands; let the operator run them.
All commands below are **verify at build** (SDK + Lume surfaces drift).

**Local — `lume` (macOS) / Docker (Linux), the default backend:**

```bash
# macOS VM backend — install Lume (Apple Virtualization Framework)
curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh | bash

# Pull a base image — FIRST PULL IS A MULTI-GB "COFFEE BREAK", not a hang
# (the macOS image is ~30GB; it downloads once, then is cached)
lume pull macos-sequoia-cua:latest
lume ls   # confirm the image is present

# Linux container backend — Docker Desktop / engine running is enough; no lume.
```

**The Sandbox SDK** (drives the provisioned machine, both backends):

```bash
# Cua's quickstart requires Python 3.12+ (lists 3.12/3.13). flow-next itself is 3.8+,
# so install into a dedicated venv: python3.12 -m venv .cua && .cua/bin/pip install cua
pip install cua   # MIT base; the omni/vision extras are NOT needed here — see Licensing

# IMPORTANT for the "local = zero-network" promise: the `cua` package ships
# anonymous usage telemetry ENABLED by default. For a truly offline local run,
# opt out — export before driving (or set telemetry_enabled=False in code):
export CUA_TELEMETRY_ENABLED=false
```

> **The "zero-network" local backend is only fully offline with telemetry disabled**
> (`CUA_TELEMETRY_ENABLED=false`). Without the opt-out, the SDK still phones home
> anonymous usage stats even on the local backend — set it, or soften the offline
> claim for your environment.

**Cloud — explicit opt-in only** (bills + data egress):

```bash
# 1. Sign in at cua.ai → Dashboard → API Keys → New API Key
# 2. Export the key ONLY when the operator has chosen the cloud for this run:
export CUA_API_KEY=sk_cua-...
```

For the full sandbox API and current image catalog, point the user at upstream
[`libs/cua-sandbox`](https://github.com/trycua/cua/tree/main/libs/python/cua-sandbox)
and the [Sandbox SDK docs](https://cua.ai/docs).

### Provision → drive → tear down (no leaked VMs)

The rung **owns the VM lifecycle** and must tear the sandbox down on **success
AND on error/abort** — a provisioned VM left running leaks cost (cloud) or
local resources. The upstream **ephemeral** lifecycle gives this for free: the
context manager auto-destroys the sandbox on block exit, error path included.
Prefer it. (SDK shape **verify at build** — names below are from the upstream
docs, not a live run.)

```python
import asyncio
from cua import Sandbox, Image

async def main():
    # local=True → the zero-network local backend (Docker/Lume/QEMU); the DEFAULT here.
    # Omit local=True ONLY when the operator opted into the cloud (CUA_API_KEY set) — bills + egress.
    async with Sandbox.ephemeral(Image.linux(), local=True) as sb:   # ← auto-destroyed on exit
        # observe → snapshot → act → verify → capture, the universal flow (SKILL.md Step 2),
        # now inside the hermetic machine. The sandbox exposes a GUI half (screenshot / AX /
        # click / type_text) and a code half (sb.shell.run(...)) over one filesystem.
        png = await sb.screenshot()              # capture — hermetic display, no host screen needed
        with open("evidence.png", "wb") as f:
            f.write(png)
    # sandbox destroyed HERE — on normal exit AND on exception. No leaked VM.

asyncio.run(main())
```

**Teardown discipline (load-bearing):**

- **`ephemeral` is the default pattern** — its `async with` tears the sandbox
  down automatically, on the error path too. Use it unless you have a reason not to.
- If you use the **persistent** form (`Sandbox.create(... name=...)` →
  `disconnect()` keeps it running), you **own** the deletion: `sb.destroy()` or
  the classmethod `Sandbox.delete(name, local=True)`. **`local=True` is required to
  delete a *local* sandbox — the default `local=False` targets the cloud namespace,
  so `Sandbox.delete(name)` after a `local=True` create silently leaves the local
  VM running** (the exact leak this rung exists to avoid). Only use the persistent
  form when state must outlive the run, and delete it explicitly. (Verify at build.)
- **On error/abort, still tear down.** Never leave a half-driven VM running —
  wrap non-ephemeral lifecycles so an exception still reaches `destroy()`.
- **`Sandbox.list()` is the leak audit** — list and reap orphaned sandboxes if a
  run died without cleanup. (Verify at build.)

### First-pull "coffee break" — not a hang

The **first** `lume pull` of a macOS image downloads a **multi-GB** disk image
(~30GB for the macOS image; verify at build) and **provisioning a fresh VM takes
seconds-to-minutes**. Surface this up front — *"first run pulls a multi-GB image,
this is a one-time coffee break, not a hang"* — so a long first pull isn't
mistaken for a stall and killed. Subsequent runs reuse the cached image and are
fast. (Containers — the Linux backend — skip the multi-GB VM image and start in
seconds.)

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
screenshot_path, console_path}` accepts both **`cua-driver`** (local) and
**`cua-sandbox`** (the headless/CI surface) as valid free-form `driver_rung`
values with **no schema or code change** — the `/flow-next:qa` ↔ flow-next-drive
(fn-51↔fn-53) read-and-drive seam and the universal flow are unchanged. On the
local driver's **AX-only evidence** mode (Screen Recording absent), the AX tree
is the captured live-state evidence and `screenshot_path` is reported as
unavailable — QA decides whether that meets its bar. The **sandbox** captures a
hermetic-display screenshot (`sb.screenshot()`) with no host screen, so it has no
permission-split caveat. Everything downstream (scenario authoring, bug filing,
verdict) stays QA's concern.

## Drift-prone facts — **verify at build**

Cua moves fast (the live run was 0.6.8). Confirm against current upstream at build:

- **MCP command surface** — the tool names/fields (`start_session`,
  `launch_app`, `get_window_state` and its `element_index` / `role` / `label` /
  `frame` / `screenshot_png_b64` shape, `click`, `type_text`, `press_key` / `hotkey`, `kill_app`,
  `end_session`), the `self_activation_suppressed` background signal, and the CLI
  subcommands (`mcp`, `serve`, `doctor`, `permissions status` / `grant`,
  `skills install`).
- **Install + wiring** — the `install.sh` / `install.ps1` URLs, the `claude mcp
  add` form, and the Codex `[mcp_servers.cua-driver]` shape.
- **Permission model** — the macOS Accessibility-vs-Screen-Recording split, the
  `com.trycua.driver` attribution, and the daemon-restart-to-pick-up-grant rule.
- **Sandbox provisioning API** — the `cua` SDK lifecycle surface
  (`Sandbox.ephemeral` / `create` / `connect` / `destroy` / `delete` / `list`,
  the `local=True` local-vs-cloud switch, `Image.linux()` and the image catalog),
  the local backend matrix (`lume`/Apple-Virtualization on macOS, Docker on
  Linux, QEMU/Hyper-V on Windows), the `lume pull` image name + ~30GB size, and
  the cua.ai cloud `CUA_API_KEY` opt-in surface. **None of this was validated
  live** — the local *driver* was; the *sandbox* was not. Verify every claim
  before relying on it.
- **License-extra boundary** — that the MIT `cua-driver` MCP is the
  default-path-complete set and `cua-agent[omni]` (ultralytics AGPL-3.0) /
  OmniParser (CC-BY-4.0) remain optional, never-auto-installed extras.

## Graceful degradation (load-bearing)

Cua Driver is never required. When it's absent, fall through — never fail silently.

| Situation | Behavior |
|-----------|----------|
| No display / headless host (cloud VM, Linux, CI), **a local sandbox backend usable** (`lume`/Docker/QEMU) | This is the **Cua Sandbox** rung — provision a hermetic VM/container (local, zero-network default), drive inside it, **tear it down each run** (no leaked VMs). Surface the first-pull multi-GB "coffee break." |
| No display / headless host, **no local backend and no opted-in cloud** | No native driver reachable at all (local driver + Computer Use both need a display). **Document the limitation and stop** — print the sandbox install (`lume`/Docker) so the operator can enable it; for web/Chromium, the web ladder still runs. Never auto-select the billing cloud. |
| Sandbox: **cloud chosen but `CUA_API_KEY` unset** (or key set but operator didn't opt into the cloud) | **Do not egress silently.** The cloud bills and receives the driven screen — it is opt-in per run. Use the local backend, or instruct the operator to set `CUA_API_KEY` + explicitly choose the cloud. |
| `cua-driver` not installed / MCP not registered | **Detect-and-instruct** — print the install + wiring commands (you can't install for the user). Fall to Codex/Claude **Computer Use** → documented-limitation. Don't block — run whatever the web ladder reaches meanwhile. |
| macOS, installed, but **Accessibility not granted** | Only no-grant reads work; **no driving**. Guide the user through `cua-driver permissions grant` + a daemon restart (you can't grant OS permissions for them). Fall to Computer Use meanwhile. |
| macOS, driving works, but **Screen Recording not granted** | Drives fully; **AX-only evidence** — surface "Screen Recording not granted ⇒ AX-only evidence, no screenshot." Do not emit an empty screenshot as if captured. |
| App is **Chromium-backed (Electron / WebView2)** | **Not this rung** — drive on the **web ladder** by CDP-attach (agent-browser `--cdp` / `--auto-connect`; chrome-devtools-mcp `--browser-url`), even though `launch_app` exposes the debug ports. Even headless/CI Chromium is the web ladder, not a provisioned desktop VM. |
| App is **genuinely native / non-CDP webview** and **no native driver at all** (no Cua Driver, no Computer Use, no sandbox backend) | **Document the limitation and stop — do not fail silently.** Continue with code review + whatever the spec allows; surface the gap. |
| App is **iOS / iPadOS** | Out of scope — defer to the community iOS simulator skills. (Cua's Android sandbox is also out of scope here.) |

## Limits

- **Never a hard dependency.** If neither the local driver nor a sandbox backend
  is present, fall through per the table — the pass still completes. agent-browser
  stays the only assumed-present driver; flowctl never imports or requires Cua.
- This rung is for **true-native + non-CDP webviews only** — local driver *and*
  sandbox alike. Anything Chromium (Electron / WebView2) → the web ladder
  ([agent-browser.md](agent-browser.md), [chrome-devtools-mcp.md](chrome-devtools-mcp.md)),
  even in CI.
- **The local driver needs a real display; the Cua Sandbox is the only headless/CI
  native surface.** Keep that distinction explicit so CI users reach for the
  sandbox, not the local driver. The sandbox is heavier (provisions a VM) and
  opt-in per run — never the default native path on an attended host.
- **The cloud sandbox backend bills and egresses the driven screen — never
  auto-selected.** The zero-network local backend (`lume`/QEMU/Docker) is the
  default; the cua.ai cloud requires an explicit per-run opt-in and a `CUA_API_KEY`.

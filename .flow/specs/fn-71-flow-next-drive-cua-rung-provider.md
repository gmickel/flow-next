# fn-71 flow-next-drive CUA rung — provider-agnostic cross-platform computer-use (Windows / native / sandbox)

## Goal & Context
<!-- scope: business -->

`/flow-next:qa` drives the running app through **flow-next-drive** (fn-51), a surface-aware driver ladder: web/Chromium surfaces use the web ladder (agent-browser → chrome-devtools-mcp → playwright → …); genuinely-native surfaces use the **Native rung (Step 4) = Computer Use**, today provided *only* by **Codex Computer Use** and/or **Anthropic Claude Computer Use**. That ties native QA to two specific providers, is **macOS/Windows-only and focus-stealing** (Computer Use takes over the real screen + cursor), and is **never available on a headless / CI / Linux path** — so native-app QA simply can't run unattended or in CI today.

[trycua/cua](https://github.com/trycua/cua) (MIT) is open-source, **provider-agnostic** computer-use infrastructure exposed as an **MCP server** (`cua-driver mcp`). It adds three things the current native rung lacks: **(1)** a computer-use driver that isn't tied to Claude/Codex; **(2)** first-class **Windows + Linux** support and **background driving** ("click, type, verify without stealing the cursor or focus"); **(3)** an **Agent-Ready Sandbox SDK** — one API over any VM/container (Linux/macOS/Windows/Android, local via QEMU or cloud) — which makes native/desktop driving possible **on a headless/CI path**, the rung's current hard limitation.

This spec adds **CUA as a new option on flow-next-drive's Native rung**: detect-best-available, opt-in, never a hard dependency — exactly like every other non-default rung. It widens QA's reach (Windows, true-native, sandboxed/CI) and decouples it from any single Computer-Use provider, without changing the universal flow or QA's own workflow.

**Validated locally (cua-driver 0.6.8, macOS aarch64, 2026-06):** the driver exposes ~40 MCP tools and is **accessibility-tree based** (`get_accessibility_tree` / `get_window_state` return structured elements + a Markdown rendering, not just pixels) — robust for native apps. **Background driving is real**: `launch_app` brings apps up *in the background* (target does not foreground), and an **agent-cursor overlay** + named **`start_session`** identities deliver the "click/type/verify without stealing the cursor or focus" property (and enable concurrent agents with distinct cursors). Basic read tools (`get_screen_size`, `list_apps`) work **immediately, no grant**; full screen-driving needs a one-time **macOS TCC grant** (`cua-driver permissions grant` → Accessibility + Screen Recording, attributed to `com.trycua.driver`) and ideally the daemon (`cua-driver serve`; tools fall back to in-process with a warning otherwise). CUA also ships an **optional agent skill-pack** (`cua-driver skills install`) that links into Claude/Codex/OpenClaw/OpenCode — a coexistence point to note, not a dependency.

## Architecture & Data Models
<!-- scope: technical -->

- **A new rung on the Native path (Step 4), not a new skill.** flow-next-drive stays the router; CUA is one more detected driver. The universal flow (`observe → snapshot → act → verify → capture → release`) is unchanged — only the actuation differs. A per-rung reference `references/cua.md` carries the command/MCP detail (mirroring `references/computer-use.md`).
- **Two CUA surfaces, both via the host agent driving an MCP (agentic):**
  - **Cua Driver** (`cua-driver mcp`) — background computer-use on the *local* machine (macOS / Windows / Linux). The host calls the driver's MCP tools (screenshot / click / type / verify). Detection: the cua-driver MCP is registered, or `command -v cua-driver`.
  - **Cua Sandbox SDK** — drive an app inside an **isolated VM/container** (any OS) for hermetic or **headless/CI** native runs. This is the rung that lifts the "Computer Use is never on a CI path" limitation. Optional, heavier (provisions a VM); detection: `cua` SDK / `lume` present, or a configured cua.ai endpoint.
- **Native-rung precedence is an explicit ordered list (not a single top-down probe).** Unlike the web ladder's pure availability ordering, the Native rung now mixes an *availability* probe with a *quality* preference (background beats screen-takeover) and a *path* split (attended vs headless). `references/cua.md` states the order explicitly to resolve how R4 and R5 compose: **(attended path)** 1. cua-driver background → 2. Codex/Claude Computer Use (screen-takeover) → 3. documented-limitation; **(headless/CI path)** the **cua-sandbox** rung is the *only* option (local Computer Use can't run there) — it ranks below local-takeover for the *attended* path purely on cost/latency, but is first (and only) on the *headless* path. So R4 (prefer background when attended) and R5 (sandbox for CI) don't conflict — they apply to different paths.
- **Opt-in prerequisite, zero-dep contract intact — detect-and-instruct, never auto-install.** CUA is an external install (`cua-driver` / the `cua` SDK / `lume`), detected and optional — never imported by `flowctl`, never assumed present, never on a path that has no display *unless* the Sandbox SDK provides one. The rung **never runs `pip install …` for the user** (the same no-auto-install consent rule `/flow-next:map` applies to `clawpatch`): it detects, and points the user at the install. Base install stays zero-dep; the rung adds nothing to the uninstall path.
- **Local-VM sandbox is the default; cua.ai cloud is explicit opt-in.** The Sandbox rung has two backends with very different privacy/cost profiles: **local** (`lume`/QEMU — zero-network, default) and **cloud** (`cua.ai` — a hosted SaaS that bills and receives the driven screen/data). The cloud endpoint is **never auto-selected**; `references/cua.md` calls out the credential + cost + data-egress implications, and the local backend is the default sandbox path (consistent with the no-SaaS posture).
- **Surface routing unchanged:** Windows **WebView2** stays surface B (CDP, web ladder) — CUA is for **true-native** surfaces and for **sandboxed/CI** native runs, not for Chromium-backed apps that CDP already drives.

## API Contracts
<!-- scope: technical -->

- **Detection (drive Step 4 + the degradation table):** add CUA probes — cua-driver MCP registered (or `command -v cua-driver`; confirm health via `cua-driver doctor`) ⇒ background-driver rung; `cua` SDK / `lume` / configured cua.ai ⇒ sandbox rung. On macOS also surface the TCC-grant state (`cua-driver permissions status`) so the user is told to `permissions grant` before a drive needs Screen Recording. Surface present AND absent in the rung report, same as other ladder probes.
- **Install + wiring (documented in `references/cua.md` and the docs):** the upstream installers — macOS/Linux `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh)"`, Windows `irm https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.ps1 | iex` — then the MCP wiring `claude mcp add --transport stdio cua-driver -- cua-driver mcp` (Claude; the reference presents the wiring host-agnostically so the Codex mirror stays clean), the one-time `cua-driver permissions grant` on macOS, and a pointer to upstream `libs/cua-driver/README.md` for sandbox/cloud operations. flow-next **detects and instructs** — it never runs these for the user.
- **Reference:** `references/cua.md` — availability detection, install/permission walkthrough (presented host-agnostically: "register the cua-driver MCP with your host", **not** a verbatim Claude-only `claude mcp add …` command, so the Codex mirror stays clean under `sync-codex.sh`), the driving loop in CUA MCP/SDK terms, the explicit Native-rung precedence list, sandbox provisioning + teardown (local vs cloud), safety/hygiene, a **"drift / verify-at-build" section** (the MCP command surface, sandbox provisioning API, and the AGPL-extra boundary all drift as upstream repackages — mirroring `computer-use.md`'s verify-at-build discipline), and the graceful-degradation entry. No driver command detail leaks into `SKILL.md`.
- **Evidence tuple unchanged:** QA's `{driver_rung, target_url, viewport, screenshot_path, console_path}` gains `cua-driver` / `cua-sandbox` as valid `driver_rung` values; everything downstream (QA scenario/verdict) is untouched — the seam fn-51↔fn-53 is preserved.
- **Cross-platform:** canonical Claude tool names in the canonical file; `sync-codex.sh` regenerates the Codex mirror. CUA's own Codex support is orthogonal (it's a driver, not a host).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Never a hard dependency.** agent-browser stays the only assumed-present driver; a pass must still complete with no CUA installed (fall to Computer Use, then to documented-limitation).
- **Sandbox cost/latency.** Provisioning a VM is heavy (seconds–minutes + disk); the sandbox rung is opt-in per run, never the default native path. Always tear the sandbox down (release step) — no leaked VMs.
- **Open debug/again exposure.** The local cua-driver controls the real machine; treat it like Computer Use for safety/hygiene (the operator consents; never on an unattended shared box without the sandbox).
- **Licensing — documented, never auto-installed (concrete actor).** Core is MIT (the `cua-driver` MCP, the everyday path); the optional `cua-agent[omni]` pulls ultralytics (AGPL-3.0) and OmniParser is CC-BY-4.0. The rung's enforcement is the same as `/flow-next:map`'s no-auto-install rule: `references/cua.md` *documents* which extras are MIT-safe vs AGPL/CC-BY, and the rung **never runs `pip install cua-agent[omni]`** for the user. R7 confirms the **default driving path (background `cua-driver` MCP) uses only MIT components and needs none of the omni/OmniParser vision stack** — if that turns out false at build, the "default path is MIT-only" claim must be corrected, not the rule relaxed.
- **Headless/CI is the sandbox rung's job, not the local driver's** — `cua-driver` still needs a display; only the Sandbox SDK provides a hermetic display for CI. Keep that distinction explicit so CI users reach for the right one.
- **Autonomy-safe:** detection + driving never prompt; an unavailable rung degrades to the next, consistent with fn-51's never-block ladder and `/flow-next:qa`'s BLOCKED-not-PASS rule when no driver is reachable.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flow-next-drive's Native rung (Step 4) documents CUA as a detected, optional driver with two surfaces — local **Cua Driver** (background computer-use, macOS/Windows/Linux via MCP) and **Cua Sandbox** (isolated VM/container, any OS). No new skill; it's a rung.
- **R2:** A `references/cua.md` rung reference exists with the **concrete install + wiring** (macOS/Linux `curl … install.sh`, Windows `irm … install.ps1 | iex`, `claude mcp add … cua-driver mcp`, the one-time macOS `cua-driver permissions grant` for Accessibility + Screen Recording, the optional `cua-driver serve` daemon, and a pointer to upstream `libs/cua-driver/README.md` for sandbox/cloud), plus detection, driving loop, sandbox provision/teardown, safety, degradation — `SKILL.md` carries no CUA command detail, only the detect/route line + ladder/table entries.
- **R3:** Detection is probe-based and graceful: cua-driver MCP / `cua` SDK / `lume` / cua.ai endpoint detected ⇒ rung available; absent ⇒ fall to Codex/Claude Computer Use, then the terminal documented-limitation rung. CUA is never assumed present, never imported by flowctl, never a hard dep.
- **R4:** `references/cua.md` states the **explicit Native-rung precedence** for both paths — attended: cua-driver background → Computer Use → documented-limitation; headless/CI: cua-sandbox only — so R4's "prefer background" and R5's "sandbox for CI" compose without conflict (different paths). Web/Chromium surfaces (A/B) are unaffected.
- **R5:** The **Sandbox** rung enables native/desktop driving on a **headless/CI path** (the current hard limitation), provisioning a hermetic display and tearing it down each run; **local `lume`/QEMU is the default sandbox backend, cua.ai cloud is explicit opt-in** (credential/cost/data-egress noted, never auto-selected). Opt-in per run, never the default native path.
- **R6:** QA's evidence tuple accepts `cua-driver` / `cua-sandbox` as `driver_rung`; the fn-51↔fn-53 read-and-drive seam and the universal flow are unchanged. `references/cua.md` includes a **drift / verify-at-build section** (MCP command surface, sandbox API, license-extra boundary).
- **R7:** Licensing — `references/cua.md` documents which extras are MIT-safe vs AGPL (`cua-agent[omni]`/ultralytics) / CC-BY (OmniParser); the rung **never auto-installs** any extra (detect-and-instruct, per the `/map`/`clawpatch` rule); the **default driving path (background `cua-driver` MCP) uses only MIT components** and needs no omni/OmniParser stack (correct the claim, not the rule, if untrue at build).
- **R8:** Cross-platform parity — canonical Claude names; `sync-codex.sh` regenerates cleanly. **Full documentation sweep** (per CLAUDE.md doc-update discipline): the repo `flow-next-drive` SKILL Step 4 + `references/cua.md` + any drive/QA docs that list driver rungs; **flow-next.dev** — the drive page (add the CUA rung + the install/permission instructions verbatim), BOTH navbars if a new page is added, the changelog entry, and `FLOW_NEXT_VERSION`; plugin version bumped per release process. (No GF-microsite / AI-x-SDLC-guide change expected for a driver rung — that surface matters for pipeline/QA/tracker changes, not driver internals.)

## Boundaries
<!-- scope: business -->

- **A driver rung, not a re-architecture** — flow-next-drive stays the router; the universal flow and QA's workflow are untouched. CUA orchestrated via its MCP/SDK; never reimplemented.
- **Not for web/Chromium surfaces** — CDP (web ladder) already drives those; CUA is for true-native and sandboxed/CI native runs.
- **Opt-in, never a hard dependency** — base install stays zero-dep; agent-browser remains the only assumed driver.
- **iOS/iPadOS stays out of scope** (existing drive boundary) — CUA's Android sandbox support is not in scope here either; this spec targets desktop (macOS/Windows/Linux) native + sandbox.
- **Not a QA-workflow change** — scenario authoring, bug filing, and the verdict remain `/flow-next:qa`'s concern (and any pipeline-stage work is a separate spec).

## Decision Context
<!-- scope: both -->

### Motivation
The native rung is the weakest part of the driver ladder: provider-locked (Codex/Claude), platform-limited (macOS/Windows), focus-stealing, and absent on CI. CUA (MIT, MCP-exposed, cross-platform, background, sandboxable) is the natural rung to fix all four at once — and it fits the existing detect-best-available ladder pattern with zero architectural change.

### Implementation Tradeoffs
- **Rung, not rewrite:** the ladder was built for exactly this — add a probe + a reference, prefer it when present, degrade when absent. No change to the universal flow or the fn-51↔fn-53 seam.
- **MCP-driven (agentic), consistent with the architecture rule:** the host agent calls CUA's MCP tools / SDK — judgment (what to click, did it work) stays in the host; CUA is pure actuation. No deterministic wrapper engine.
- **Two surfaces, different costs:** the local background driver is cheap and the everyday win (no focus-steal, Windows, provider-agnostic); the sandbox is heavier but uniquely unlocks headless/CI native QA — kept opt-in per run.
- **Opt-in prereq over bundling:** consistent with the zero-dep base contract and the `clawpatch`/`/map` precedent; CUA's heavier footprint (VMs, optional AGPL extras) makes bundling wrong.

## Strategy Alignment
- **Cross-platform parity track** — extends native QA to Windows + Linux + sandbox, the platforms the current Computer-Use rung can't reach; canonical names + sync-codex mirror.
- **Opt-in-prereq carve-out** — base `flowctl` stays zero-dep; CUA is a detected, optional rung that adds nothing to the uninstall path (single `.flow/` dir).
- **"Host agent IS the intelligence"** — CUA is actuation driven by the host via MCP; no judgment moves into a deterministic engine.
- Strengthens `/flow-next:qa` (and any future QA-in-pipeline work, separate spec) by making the live-app driver reachable in more environments.

## Conversation Evidence
> user: "we have our QA skill, currently we don't offer https://github.com/trycua/cua afaik, this might be interesting to make it less tied to claude and codex computer use? wider support incl windows etc?"

Reference: [trycua/cua](https://github.com/trycua/cua) (MIT) — Cua Driver (background computer-use, macOS/Windows/Linux, MCP), Cua Sandbox SDK (any-OS VM/container), Lume (Apple-Silicon VM mgmt). Integrates with Claude/Cursor/Codex/custom via CLI + MCP. Current native rung: `plugins/flow-next/skills/flow-next-drive/SKILL.md` Step 4 + `references/computer-use.md`.

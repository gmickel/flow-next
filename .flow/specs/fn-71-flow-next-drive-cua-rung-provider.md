# fn-71 flow-next-drive CUA rung — provider-agnostic cross-platform computer-use (Windows / native / sandbox)

## Goal & Context
<!-- scope: business -->

`/flow-next:qa` drives the running app through **flow-next-drive** (fn-51), a surface-aware driver ladder: web/Chromium surfaces use the web ladder (agent-browser → chrome-devtools-mcp → playwright → …); genuinely-native surfaces use the **Native rung (Step 4) = Computer Use**, today provided *only* by **Codex Computer Use** and/or **Anthropic Claude Computer Use**. That ties native QA to two specific providers, is **macOS/Windows-only and focus-stealing** (Computer Use takes over the real screen + cursor), and is **never available on a headless / CI / Linux path** — so native-app QA simply can't run unattended or in CI today.

[trycua/cua](https://github.com/trycua/cua) (MIT) is open-source, **provider-agnostic** computer-use infrastructure exposed as an **MCP server** (`cua-driver mcp`). It adds three things the current native rung lacks: **(1)** a computer-use driver that isn't tied to Claude/Codex; **(2)** first-class **Windows + Linux** support and **background driving** ("click, type, verify without stealing the cursor or focus"); **(3)** an **Agent-Ready Sandbox SDK** — one API over any VM/container (Linux/macOS/Windows/Android, local via QEMU or cloud) — which makes native/desktop driving possible **on a headless/CI path**, the rung's current hard limitation.

This spec adds **CUA as a new option on flow-next-drive's Native rung**: detect-best-available, opt-in, never a hard dependency — exactly like every other non-default rung. It widens QA's reach (Windows, true-native, sandboxed/CI) and decouples it from any single Computer-Use provider, without changing the universal flow or QA's own workflow.

## Architecture & Data Models
<!-- scope: technical -->

- **A new rung on the Native path (Step 4), not a new skill.** flow-next-drive stays the router; CUA is one more detected driver. The universal flow (`observe → snapshot → act → verify → capture → release`) is unchanged — only the actuation differs. A per-rung reference `references/cua.md` carries the command/MCP detail (mirroring `references/computer-use.md`).
- **Two CUA surfaces, both via the host agent driving an MCP (agentic):**
  - **Cua Driver** (`cua-driver mcp`) — background computer-use on the *local* machine (macOS / Windows / Linux). The host calls the driver's MCP tools (screenshot / click / type / verify). Detection: the cua-driver MCP is registered, or `command -v cua-driver`.
  - **Cua Sandbox SDK** — drive an app inside an **isolated VM/container** (any OS) for hermetic or **headless/CI** native runs. This is the rung that lifts the "Computer Use is never on a CI path" limitation. Optional, heavier (provisions a VM); detection: `cua` SDK / `lume` present, or a configured cua.ai endpoint.
- **Ladder placement & precedence (within Native rung):** when a native (surface-C) target is detected, probe Native-rung drivers in a detect-best-available order. CUA's **background, non-focus-stealing** driver is preferred over screen-takeover Computer Use **when present**, because it doesn't hijack the operator's machine; Codex/Claude Computer Use remain valid rungs; terminal rung stays "document the limitation." Web/Chromium surfaces (A/B) are unaffected — they keep using the web ladder (CDP), never CUA.
- **Opt-in prerequisite, zero-dep contract intact.** CUA is an external install (`cua-driver` / the `cua` SDK / `lume`), detected and optional — never imported by `flowctl`, never assumed present, never on a path that has no display *unless* the Sandbox SDK provides one. Mirrors the strategy's opt-in-prereq carve-out (e.g. `/flow-next:map` wrapping `clawpatch`): base install stays zero-dep; the rung adds nothing to the uninstall path.
- **Surface routing unchanged:** Windows **WebView2** stays surface B (CDP, web ladder) — CUA is for **true-native** surfaces and for **sandboxed/CI** native runs, not for Chromium-backed apps that CDP already drives.

## API Contracts
<!-- scope: technical -->

- **Detection (drive Step 4 + the degradation table):** add CUA probes — cua-driver MCP registered (or `command -v cua-driver`) ⇒ background-driver rung; `cua` SDK / `lume` / configured cua.ai ⇒ sandbox rung. Surface present AND absent in the rung report, same as other ladder probes.
- **Reference:** `references/cua.md` — availability detection, install/permission walkthrough, the driving loop in CUA MCP/SDK terms, sandbox provisioning + teardown, safety/hygiene, and the graceful-degradation entry. No driver command detail leaks into `SKILL.md`.
- **Evidence tuple unchanged:** QA's `{driver_rung, target_url, viewport, screenshot_path, console_path}` gains `cua-driver` / `cua-sandbox` as valid `driver_rung` values; everything downstream (QA scenario/verdict) is untouched — the seam fn-51↔fn-53 is preserved.
- **Cross-platform:** canonical Claude tool names in the canonical file; `sync-codex.sh` regenerates the Codex mirror. CUA's own Codex support is orthogonal (it's a driver, not a host).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Never a hard dependency.** agent-browser stays the only assumed-present driver; a pass must still complete with no CUA installed (fall to Computer Use, then to documented-limitation).
- **Sandbox cost/latency.** Provisioning a VM is heavy (seconds–minutes + disk); the sandbox rung is opt-in per run, never the default native path. Always tear the sandbox down (release step) — no leaked VMs.
- **Open debug/again exposure.** The local cua-driver controls the real machine; treat it like Computer Use for safety/hygiene (the operator consents; never on an unattended shared box without the sandbox).
- **Licensing note (surface in the reference):** core is MIT, but the optional `cua-agent[omni]` pulls ultralytics (AGPL-3.0) and OmniParser is CC-BY-4.0 — the rung must not silently pull AGPL deps; document which extras are safe for the default path.
- **Headless/CI is the sandbox rung's job, not the local driver's** — `cua-driver` still needs a display; only the Sandbox SDK provides a hermetic display for CI. Keep that distinction explicit so CI users reach for the right one.
- **Autonomy-safe:** detection + driving never prompt; an unavailable rung degrades to the next, consistent with fn-51's never-block ladder and `/flow-next:qa`'s BLOCKED-not-PASS rule when no driver is reachable.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flow-next-drive's Native rung (Step 4) documents CUA as a detected, optional driver with two surfaces — local **Cua Driver** (background computer-use, macOS/Windows/Linux via MCP) and **Cua Sandbox** (isolated VM/container, any OS). No new skill; it's a rung.
- **R2:** A `references/cua.md` rung reference exists (detection, install/permission, driving loop, sandbox provision/teardown, safety, degradation) — `SKILL.md` carries no CUA command detail, only the detect/route line + ladder/table entries.
- **R3:** Detection is probe-based and graceful: cua-driver MCP / `cua` SDK / `lume` / cua.ai endpoint detected ⇒ rung available; absent ⇒ fall to Codex/Claude Computer Use, then the terminal documented-limitation rung. CUA is never assumed present, never imported by flowctl, never a hard dep.
- **R4:** Within the Native rung, CUA's **background, non-focus-stealing** local driver is preferred over screen-takeover Computer Use when both are present; Computer Use remains a valid fallback. Web/Chromium surfaces (A/B) are unaffected.
- **R5:** The **Sandbox** rung enables native/desktop driving on a **headless/CI path** (the current hard limitation), provisioning a hermetic display and tearing it down each run; it is opt-in per run and never the default native path.
- **R6:** QA's evidence tuple accepts `cua-driver` / `cua-sandbox` as `driver_rung`; the fn-51↔fn-53 read-and-drive seam and the universal flow are unchanged.
- **R7:** Licensing hygiene — the default path uses only MIT/permissive CUA components; AGPL (`cua-agent[omni]`/ultralytics) and CC-BY (OmniParser) extras are flagged in the reference and never pulled silently.
- **R8:** Cross-platform parity — canonical Claude names; `sync-codex.sh` regenerates cleanly. Docs + flow-next.dev (drive page) updated; plugin version bumped per release process.

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

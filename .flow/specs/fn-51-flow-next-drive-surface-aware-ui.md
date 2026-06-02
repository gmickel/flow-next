## Conversation Evidence

> user: "which browser driving tool does ray recommend in his skill, i think he uses the build-in codex one too, not just agent-browser like we have here."
> user: "i agree with all of this, the ladder for browser tools so flow-next can support as many as possible, i assume this would mean a rewrite of our browser skill that should probably be renamed to flow-next:browser or something so it doesnt collide with codex browser skills etc."
> user: "wonder if we should not call it browser but another name that would also cover non browser apps that could be ran/automated using computer use, ie. non electron desktop apps, or should that be separate"
> user: "surely the only thing that changes in terms of skill scope is a conditional that says something like if this is a browser app then x, otherwise y"
> user: (name decision) "flow-next-drive"
> [context: RayFernando1337/rayfernando-skills browser-playbook.md + computer-use-playbook.md (Apache-2.0). Driver ladder: cursor-ide-browser -> chrome-devtools-mcp -> browser-use -> Playwright -> Codex Computer Use -> manual. Computer Use is "a fallback for reach, not the default driver"; the only way to reach native macOS/Electron apps; graceful-degradation table: native + CU unavailable -> drive the Electron/Tauri dev-server URL in a browser.]
> [context: flow-next ships skills/browser/ (frontmatter name: browser), hardwired to the agent-browser CLI; sync-codex.sh renames it to agent-browser in the Codex mirror (codex/skills/agent-browser/) -- colliding with the user's global agent-browser skill and Codex-native browser skills.]
> [correction (verified): Ray's "Computer Use is the only way to reach native macOS/Electron apps" is too strong. Electron / WebView2 apps are Chromium and agent-browser already drives them over CDP (`references/advanced.md`: `--cdp <port>` ... "control Electron apps ... WebView2 apps"). Computer Use is the SOLE option only for genuinely native (AppKit/SwiftUI) apps and webviews with no CDP -- e.g. macOS WKWebView, which Tauri uses on macOS (Windows WebView2 IS CDP-drivable). Also: Anthropic "Claude" Computer Use (API `computer` tool) is evaluated as a second native rung alongside Codex CU.]

## Goal & Context
<!-- scope: business -->
<!-- Source-tag breakdown: 55% [user] / 30% [paraphrase] / 15% [inferred] -->

flow-next ships a `browser` skill hardwired to a single driver (Vercel's agent-browser CLI), and named so it collides: its Codex-mirror rename to `agent-browser` clashes with the user's global `agent-browser` skill and with Codex-native browser skills. The skill should **drive any UI surface — a web app, a Chromium-backed desktop app (Electron / WebView2, reachable over CDP), or a genuinely native app (AppKit/SwiftUI macOS, or a non-CDP webview like macOS WKWebView/Tauri) — not just browsers**, detecting the surface, picking the right driver for it, and degrading gracefully where a richer driver is absent. Renamed `flow-next-drive` to fix the collision and signal the broader reach. This also unblocks a future `/flow-next:qa` skill, which needs a real driver ladder to drive live apps. The ladder + surface structure borrows from Ray Fernando's running-bug-review-board (Apache-2.0 — credited in CHANGELOG + skill).

## Quick commands

```bash
# skill renamed + discoverable; frontmatter name matches dir
ls plugins/flow-next/skills/flow-next-drive/SKILL.md
grep -m1 '^name:' plugins/flow-next/skills/flow-next-drive/SKILL.md      # -> name: flow-next-drive
# SKILL.md stays a lean router (well under the ~500-line cap)
wc -l plugins/flow-next/skills/flow-next-drive/SKILL.md
# Codex mirror regenerates; no leftover 'browser'/'agent-browser' skill name
bash scripts/sync-codex.sh && ls plugins/flow-next/codex/skills/flow-next-drive/SKILL.md
# rename fully swept (bare + variable-form), no stray refs
grep -rniE '\bbrowser\b' plugins/flow-next/skills/ scripts/sync-codex.sh | grep -iv flow-next-drive || echo "clean"
```

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — removes the `browser` (Claude/Droid) vs `agent-browser` (Codex mirror) name asymmetry; canonical Claude-native names + `sync-codex.sh` rewrite remain the single source of truth, and the renamed skill loads identically on Claude / Codex / Droid.

## Architecture & Data Models
<!-- scope: technical -->

The skill is restructured from "agent-browser command reference" into a **surface-aware driver ladder**. A top-level step detects the target surface and dispatches on a conditional (browser/web app -> web driver path; native desktop -> Computer Use path). Both paths share one **universal flow** (`observe / navigate -> snapshot -> act on fresh refs -> capture evidence -> release`); only the actuation and the per-surface reference differ. Layout: lean entry point (surface detection + universal flow + the ladder), then per-driver / per-surface reference files. The existing references (commands, advanced, auth, snapshot-refs, session-management, proxy, debugging) fold into the web-surface / agent-browser rung's reference; surface-detection, the universal flow, and the ladder itself are net-new. Canonical files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror (single source of truth).

## Edge Cases & Constraints
<!-- scope: technical -->

- Most execution environments (cloud VMs, Linux, CI) lack any Computer Use (Codex or Claude) — it must never be a hard dependency, and a pass must still succeed with whatever driver is present.
- **Electron / WebView2 apps are Chromium → reachable by the web ladder over CDP** (attach to the app's remote-debugging port: `agent-browser --cdp <port>` / `--auto-connect`; chrome-devtools-mcp `--browser-url`) — NOT a Computer-Use-only case. Computer Use is the *sole* option only for genuinely native (AppKit/SwiftUI) apps and webviews exposing no CDP. Per-platform caveat: Windows WebView2 is CDP-drivable; macOS WKWebView (what Tauri uses on macOS) generally is not → verify per platform.
- Claude Computer Use is an API-level tool, not a CLI/MCP the skill can shell out to like agent-browser — it needs its own harness (Anthropic computer-use API loop + a controlled display/sandbox, or an MCP wrapper). Optional, detected rung; verify the tool/beta-header version at build (drifts).
- agent-browser is the only driver assumed present; every other rung (chrome-devtools-mcp, cursor-ide-browser, Playwright, Codex/Claude Computer Use) is detected and optional.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Canonical skill renamed `browser` -> `flow-next-drive` (directory, frontmatter `name`, and surfaced invocation `flow-next:flow-next-drive`), matching the `flow-next-*` naming convention used by every other plugin skill. [user]/[paraphrase]
- **R2:** Codex mirror is also named `flow-next-drive` (drop the `agent-browser` rename in `sync-codex.sh`), resolving the collision with the user's global `agent-browser` skill and with Codex-native browser skills. [paraphrase]
- **R3:** Surface detection + conditional dispatch — the skill classifies the target into one of three buckets and branches: (a) **web app** → web ladder; (b) **Chromium-backed desktop app** (Electron / WebView2) → web ladder by attaching over CDP to the app's remote-debugging port; (c) **true-native / non-CDP surface** (AppKit/SwiftUI macOS, or a webview exposing no CDP — e.g. macOS WKWebView / Tauri-on-macOS) → Computer Use. The universal flow (`observe -> act -> verify -> capture`) is shared; only actuation + the per-surface reference differ. [user]/[paraphrase]
- **R4:** Web (and Chromium-desktop) surface -> driver ladder, in priority order: agent-browser (default rung) -> chrome-devtools-mcp (auto-wait + attach-to-real-signed-in-Chrome) -> Playwright -> cursor-ide-browser MCP -> manual screenshot relay. The SAME ladder drives Electron / WebView2 apps by attaching to the app's remote-debugging port (`agent-browser --cdp <port>` / `--auto-connect`; chrome-devtools-mcp `--browser-url`) — already supported by the agent-browser skill (`references/advanced.md`). [paraphrase]
- **R5:** True-native / non-CDP surface -> **Computer Use**, driver-agnostic across what the host offers: **Codex Computer Use** (macOS/Windows) and/or **Anthropic "Claude" Computer Use** (API `computer` tool, e.g. `computer_20251124` + beta header, run via its own harness — a controlled display/sandbox or an MCP wrapper; verify version at build). Detect availability; use whichever the environment provides. Graceful degradation when no CU is present: a Chromium-backed app still drives via the web-ladder CDP attach (R4) or its dev-server URL; a genuinely native app (AppKit/SwiftUI) with no CU -> document the limitation rather than fail. Computer Use is never a hard dependency and never on a headless/no-display path; agent-browser stays the only assumed-present driver. [user]/[paraphrase]
- **R6:** Existing agent-browser references (commands, advanced, auth, snapshot-refs, session-management, proxy, debugging) fold into the web-surface / agent-browser rung's per-driver reference — no capability regression for current agent-browser users. [paraphrase]
- **R7:** Cross-platform parity preserved — canonical uses Claude-native tool names; `sync-codex.sh` is updated for the new skill name + surface/ladder content; the Codex mirror is regenerated. [strategy:Cross-platform parity]
- **R8:** Plugin version bumped (skill change, not docs-only per CLAUDE.md). Docs updated across THREE surfaces: (a) **repo** — CHANGELOG (crediting rayfernando-skills), root README, doc index `plugins/flow-next/docs/README.md`, CLAUDE.md, `.flow/usage.md`, and anywhere the old `browser` skill is referenced (platforms/skill lists); (b) **flow-next.dev** (`~/work/flow-next.dev`) — the browser/driver skill page + any guide / workflow page that references the skill by its old `browser` name (the rename touches them) + changelog entry, run the `pnpm build` gate; (c) **mickel.tech** (`~/work/mickel.tech`) — the flow-next app page, **maintainer-only (Gordon updates post-merge; contributor PRs skip it)**. [inferred]
- **R9:** The rename is surfaced as a user-facing change — migration/uninstall notes cover the old `browser` / `agent-browser` skill names so existing references don't silently break. [inferred]

## Boundaries
<!-- scope: business -->

- iOS / iPadOS app driving is OUT of scope — defer to the community iOS simulator skills (as Ray's skill does); never spin a simulator for a web-only app.
- Full native-desktop QA *workflow* (scenario authoring, bug filing, verdict) is downstream `/flow-next:qa`; this skill provides driver/actuation + the surface conditional only.
- NOT the tracker-sync bridge (separate spec, captured next).
- No MCP server (chrome-devtools-mcp, cursor-ide-browser) or Computer Use becomes a hard install dependency — drivers are detected and optional; agent-browser is the only assumed-present one.
- NOT reimplementing what a driver already does (e.g. don't reinvent Playwright or Computer Use) — the skill orchestrates drivers, it doesn't replace them.

## Decision Context
<!-- scope: both -->

The surface change is deliberately minimal — a top-level conditional (browser app -> web ladder; else -> Computer Use), not a separate skill or a heavy native subsystem. The Computer Use rung already reaches native apps, so the marginal cost of covering native desktop is the detection branch + a per-surface reference. agent-browser stays the **default rung** because it's what flow-next already ships, it's CDP-based and headless-safe, and it needs no extra install. Computer Use sits at the native branch (and as a web human-fidelity escalation) rather than the default because most execution environments (cloud VMs, Linux, CI) lack it — making it a dependency would break the common case. The ladder mirrors Ray Fernando's proven structure rather than inventing one. The rename is bundled with the rewrite so shipping a surface-aware ladder under the colliding `browser` / `agent-browser` name doesn't re-introduce the collision the user flagged.

## Early proof point

Task **fn-51.1** validates the core approach — a lean SKILL.md *router* (surface-detection conditional + universal flow + driver-ladder table + per-rung pointers) that stays well under the ~500-line cap, with the renamed `flow-next-drive` skill loading on both Claude and Codex. If SKILL.md can't stay lean once the ladder is expressed, or the renamed skill doesn't load on a platform, re-evaluate the progressive-disclosure structure before building the rung references (fn-51.2–.4).

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Rename `browser` → `flow-next-drive` (dir + frontmatter + invocation) | fn-51.1 | — |
| R2 | Codex mirror named `flow-next-drive`; drop the `agent-browser` rename in sync-codex.sh | fn-51.5 | — |
| R3 | Surface detection + conditional dispatch (web vs native) | fn-51.1 | — |
| R4 | Web driver ladder (agent-browser → chrome-devtools-mcp → Playwright → cursor-ide-browser → manual) | fn-51.1 (router/table), fn-51.3 (rung refs) | — |
| R5 | Native-desktop rung (Computer Use) + graceful degradation | fn-51.4 | — |
| R6 | Fold existing agent-browser references into the default rung; no regression | fn-51.2 | — |
| R7 | Cross-platform parity — canonical names + sync-codex.sh + regenerated mirror | fn-51.5 | — |
| R8 | Version bump + 3-surface docs (repo / flow-next.dev / mickel.tech) | fn-51.6 | — |
| R9 | User-facing rename: migration / uninstall notes | fn-51.6 | — |

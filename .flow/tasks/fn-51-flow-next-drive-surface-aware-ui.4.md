---
satisfies: [R5]
---

## Description
Add the **native rung**: `references/computer-use.md`, for **true-native (AppKit/SwiftUI) apps and webviews that expose no CDP** (e.g. macOS WKWebView, which Tauri uses on macOS). NOTE: **Electron / WebView2 are Chromium and do NOT belong here** — they drive via the web ladder by CDP-attach (see fn-51.2 agent-browser `--cdp` / `--auto-connect`, and fn-51.3 chrome-devtools-mcp `--browser-url`).

The rung is **driver-agnostic** across whatever Computer Use the host provides:
- **Codex Computer Use** (macOS + Windows — verify; **excluded in EEA/UK/Switzerland** — verify, fast-drifting): permissions (Screen Recording + Accessibility); cannot drive terminals, Codex itself, or OS permission prompts.
- **Anthropic "Claude" Computer Use** (API `computer` tool, e.g. `computer_20251124` + beta header `computer-use-2025-11-24`): it is an API-level tool, NOT a CLI/MCP — it needs its own harness (the Anthropic computer-use API loop + a controlled display/sandbox, or an MCP that wraps it). Document detection + the harness requirement; do not assume it is reachable from inside the host coding agent.

Both share the universal flow (observe -> act -> verify -> capture). Detect availability; use whichever the environment offers; verify tool/version at build (both drift).

**Graceful degradation (load-bearing):** a Chromium-backed app (Electron/WebView2) with no CU still drives via the web-ladder CDP-attach (R4) or its dev-server URL; a genuinely native app (AppKit/SwiftUI) with no CU -> document the limitation and stop, never fail silently. Computer Use is **never a hard dependency** and **never on a headless/no-display path**.

**Size:** S/M
**Files:** plugins/flow-next/skills/flow-next-drive/references/computer-use.md

## Approach
- Mirror Ray's computer-use-playbook.md graceful-degradation table. Link OpenAI's CU docs; keep our reference to the flow-next-relevant decisions (when to reach for it, how to fall through).

## Investigation targets
**Required:**
- `~/repos/rayfernando-skills/.../references/computer-use-playbook.md` — graceful-degradation table + detect-availability pattern
- `https://developers.openai.com/codex/app/computer-use` — Codex CU: availability, permissions, region limits (verify at build)
- `https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool` — Anthropic Claude CU: tool type, beta header, harness model
- spec `## Edge Cases & Constraints` (fn-51) — degradation rules + the Electron-is-CDP correction

## Acceptance
- [ ] `references/computer-use.md` covers BOTH providers (Codex CU + Anthropic Claude CU) with detect-availability + the shared universal flow
- [ ] Reference scoped to true-native + non-CDP webviews; explicitly states Electron / WebView2 use the web ladder via CDP (cross-ref the web rungs), NOT this rung
- [ ] Claude CU's harness requirement (API loop + display/sandbox or MCP wrapper; not a shell-out) documented
- [ ] availability / region / permissions / tool-version all marked "verify at build"
- [ ] "Never a dependency" + "never on a headless/no-display path" stated; graceful-degradation table present
- [ ] SKILL.md native-branch pointer resolves to this reference

## Done summary
Added references/computer-use.md — the flow-next-drive native rung — resolving the last dangling SKILL.md reference (Step 4). Covers both Computer Use providers (Codex CU + Anthropic Claude CU with its harness requirement), scopes the rung to true-native (AppKit/SwiftUI) + non-CDP webviews while explicitly routing Electron/WebView2 to the web ladder via CDP, and adds the never-a-dependency / never-headless graceful-degradation table with availability/region/permissions/tool-version marked verify-at-build.
## Evidence
- Commits: 42bfe545e10c62a682ad6956c78a175a35d01cf7
- Tests: grep/test smoke suite: file exists; SKILL.md Step 4 -> references/computer-use.md resolves; zero dangling references/*.md across whole skill (SKILL.md + all rung refs); both providers (Codex CU + Anthropic Claude CU) present; Electron/WebView2 -> web-ladder cross-ref (agent-browser.md --cdp + chrome-devtools-mcp.md --browser-url) present; Claude CU harness note (API loop + display/sandbox or MCP wrapper, not-free-from-host) present; never-a-hard-dependency + never-headless stated; graceful-degradation table present; native+no-CU -> document-and-stop not fail-silently; 8x verify-at-build markers (region/permissions/tool-version); all local md links + both provider doc URLs resolve
- PRs:
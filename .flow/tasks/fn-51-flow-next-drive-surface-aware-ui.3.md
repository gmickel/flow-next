---
satisfies: [R4]
---

## Description
Add the additional **web ladder rungs**, one reference per driver, loaded on demand:
- `references/chrome-devtools-mcp.md` — Google official; **auto-waits** (don't hand-roll waits); attach-to-real-Chrome via `--autoConnect` (Chrome 144+, shows an allow-dialog) or `--browser-url`; `--isolated`/`--headless`; the only source for Lighthouse/perf/heap; **cannot launch Chrome when the MCP server is sandboxed** (fall through on launch failure).
- `references/playwright.md` — `@playwright/cli` is token-efficient (snapshot-to-disk) → prefer for autonomous/Ralph loops; Playwright MCP for interactive state; WebKit/Firefox is the differentiator (only reach for it when non-Chrome matters); ephemeral/isolated session by default.
- `references/cursor-ide-browser.md` — host-only inside Cursor; known-flaky → detect, never depend; low rung.

Each reference: link the canonical upstream doc + the flow-next-relevant gotcha; keep to ~one screen (TOC if >100 lines); mark drift-prone items "verify at build."

**Size:** M
**Files:** references/chrome-devtools-mcp.md, references/playwright.md, references/cursor-ide-browser.md

## Approach
- Don't re-document upstream — link + the one-line gotcha that matters for our ladder. Per-driver gotchas come from practice-scout/docs-scout findings.

## Investigation targets
**Required:**
- `https://github.com/ChromeDevTools/chrome-devtools-mcp` README — connect flags + auto-wait
- `https://playwright.dev/docs/getting-started-cli` and `/getting-started-mcp` — CLI-vs-MCP token tradeoff
- `https://cursor.com/docs/agent/tools/browser` — the in-IDE tool (NOT third-party browser-tools-mcp)
- `~/repos/rayfernando-skills/.../references/browser-playbook.md` — rung framing

## Acceptance
- [ ] Three rung references exist (chrome-devtools-mcp, playwright, cursor-ide-browser)
- [ ] Each links canonical docs + the flow-next-relevant gotcha; each ≤ ~one screen
- [ ] Drift-prone facts (Chrome version floor, CU flags, `@playwright/cli` package, autoConnect dialog) marked "verify at build"
- [ ] chrome-devtools-mcp rung documents `--browser-url` attach to a **running Electron / WebView2 app** (not only a fresh Chrome), so the web ladder covers Chromium-desktop surfaces
- [ ] SKILL.md ladder pointers for these rungs resolve

## Done summary

## Evidence

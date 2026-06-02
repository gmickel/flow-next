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
Added the three web-ladder rung reference files for the flow-next-drive skill (SKILL.md Step 3 pointers now resolve): references/chrome-devtools-mcp.md (rung 2 — auto-wait, Lighthouse/perf, --browser-url attach to a running Electron/WebView2 app, --autoConnect Chrome 144+ allow-dialog, sandbox-can't-launch-Chrome caveat), references/playwright.md (rung 3 — @playwright/cli snapshot-to-disk for autonomous/Ralph vs Playwright MCP for interactive, WebKit/Firefox differentiator), and references/cursor-ide-browser.md (rung 4 — host-only inside Cursor, known-flaky, detect-never-depend). Each is one screen, links canonical upstream + the flow-next gotcha, marks drift-prone facts "verify at build". The remaining dangling SKILL.md ref (computer-use.md) is fn-51.4 scope, left as-is.
## Evidence
- Commits: 152660a932e21eaa9c266a727e5c7d39ada281fe
- Tests: smoke: all 3 rung files exist (chrome-devtools-mcp.md 59L, playwright.md 60L, cursor-ide-browser.md 50L) - each <=one screen, no TOC needed, smoke: SKILL.md ladder pointers for rungs 2-4 all resolve to files on disk; only computer-use.md remains dangling (fn-51.4 scope, left as-is per directive), content: chrome-devtools-mcp documents --browser-url attach to a RUNNING Electron/WebView2 app (not only fresh Chrome), covering Chromium-desktop surface B, content: playwright distinguishes @playwright/cli (snapshot-to-disk, token-efficient -> autonomous/Ralph) vs Playwright MCP (interactive); WebKit/Firefox as differentiator, content: cursor-ide-browser host-only inside Cursor + known-flaky -> detect-never-depend, lowest non-manual rung, drift: 5 facts marked verify-at-build (Chrome 144+ floor + allow-dialog for --autoConnect, @playwright/cli package name, sandbox-can't-launch-Chrome caveat, flag drift); CU flags live in computer-use.md (fn-51.4), facts verified live via WebFetch/WebSearch against upstream README/docs (chrome-devtools-mcp, playwright.dev getting-started-cli + browsers, cursor.com docs), markdown-lint: python fence-aware check - 1 real H1 per file, 0 skipped heading levels, all tables pipe-consistent, broken-links: 0 relative .md links (upstream-link files by design); all 9 upstream URLs return HTTP 200 via curl -L
- PRs:
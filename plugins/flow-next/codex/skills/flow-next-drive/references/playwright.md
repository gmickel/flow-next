# Playwright — rung 3 (cross-browser; CLI vs MCP)

Web-ladder rung 3 (SKILL.md Step 3). **Detected, optional.** Reach for Playwright when the repo already has it configured, you need a **headless CI-style run / large cross-browser regression suite**, or you need an engine the Chrome-only rungs can't give: **WebKit (Safari engine) or Firefox is the differentiator** — only drop to this rung over chrome-devtools-mcp when non-Chrome matters. Sessions are ephemeral / isolated by default.

Canonical, version-matched docs (read these over this file when they disagree):

- Agents CLI: <https://playwright.dev/docs/getting-started-cli>
- Playwright MCP: <https://playwright.dev/docs/getting-started-mcp>
- Browser engines: <https://playwright.dev/docs/browsers>
- Test runner: <https://playwright.dev/docs/intro>

## CLI vs MCP — pick by loop type

Two ways an agent drives Playwright. They differ in token cost and statefulness:

| | `@playwright/cli` (run as `playwright-cli`) | Playwright **MCP** |
|---|---|---|
| Best for | **Coding agents / autonomous + Ralph loops** | **Interactive, persistent agentic loops** |
| Why | Token-efficient: **snapshot-to-disk** — each command writes a YAML snapshot to a file (e.g. `.playwright-cli/page-<ts>.yml`) instead of dumping a large accessibility tree into context | Persistent state + iterative reasoning over live page structure (exploratory / long-running) |
| Cost | Avoids loading large tool schemas / verbose trees into the model context | Verbose tree in context each turn |

For flow-next autonomous / Ralph passes, **prefer `@playwright/cli`** — the snapshot-to-disk shape keeps context small over a long unattended run. Use the MCP only for interactive, human-in-the-loop exploration.

## CLI quickstart (the autonomous default)

```bash
npm install -g @playwright/cli@latest # or local dep + npx playwright-cli
playwright-cli install --skills # agent skill files
playwright-cli --help
# Each command prints a snapshot path; act on refs from the latest snapshot.
playwright-cli screenshot --filename=evidence.png
```

## Cross-browser — the reason to be on this rung

```bash
# Playwright drives Chromium, WebKit (Safari engine), and Firefox.
# WebKit / Firefox is what the Chrome-only rungs (agent-browser, chrome-devtools-mcp) can't do.
```

- Engines: **Chromium**, **WebKit** (Safari engine — not branded Safari), **Firefox**. Cross-browser regression is the differentiator; if the task is Chrome-only, stay on a higher rung (chrome-devtools-mcp / agent-browser).

## Spec-file driving (when the repo already has Playwright)

```bash
npx playwright test tests/manual/<scenario>.spec.ts --headed
# page.pause() for interactive debug; page.screenshot({ path: ... }) for evidence;
# page.context().clearCookies() for hygiene between scenarios.
# One-off scenarios: npx playwright codegen to record, then translate to steps.
```

## Drift-prone facts — **verify at build**

- **Package name `@playwright/cli`** (invoked as `playwright-cli`) — the agents-CLI package/command names are newer than the test runner and drift; confirm against `getting-started-cli` at build.
- The snapshot-to-disk path/format (`.playwright-cli/page-*.yml`) and `--skills` install flow — verify against current docs.

## Limits

- Heavier than the default rung: needs Playwright + browser binaries installed. Never hard-depend on it — it's a detected rung; fall back to agent-browser if absent.
- For a genuinely native (non-CDP) surface, Playwright doesn't apply — see the native rung (SKILL.md Step 4).

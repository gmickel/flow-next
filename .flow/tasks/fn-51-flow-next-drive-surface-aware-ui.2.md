---
satisfies: [R6]
---

## Description
Make agent-browser the **default web rung** with no capability regression. The existing 7 references (commands, advanced, auth, snapshot-refs, session-management, proxy, debugging) become the rung's docs; add `references/agent-browser.md` as the rung entry-point that SKILL.md's ladder points to, receiving the agent-browser-specific content fn-51.1 extracted from the old SKILL.md (ref-lifecycle re-snapshot rule, `--headed` daemon-reuse gotcha, `agent-browser doctor`/`install`, connect-to-Chrome, sessions).

Every command/flow the old single-driver skill supported must still be reachable through this rung (no regression).

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-drive/references/agent-browser.md (new rung entry) + existing references/{commands,advanced,auth,snapshot-refs,session-management,proxy,debugging}.md (kept; lightly reorganized under the rung)

## Approach
- Keep the 7 existing references as-is where possible — they are the agent-browser detail and are well-organized. `agent-browser.md` is the rung index + the extracted SKILL.md specifics.
- Prefer pointing at the installed CLI's own docs (`agent-browser skills get core`, `agent-browser --help`) so the rung tracks the installed version rather than drifting.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/browser/SKILL.md` — the agent-browser content fn-51.1 removed (relocate here)
- `plugins/flow-next/skills/browser/references/commands.md`, `snapshot-refs.md`, `session-management.md` — existing rung detail
- `https://github.com/vercel-labs/agent-browser` README — install/doctor + `@eN` ref model

## Acceptance
- [ ] `references/agent-browser.md` exists as the default-rung entry-point
- [ ] Existing references preserved; no command/capability from the old SKILL.md is lost (diff the old surface against the new rung)
- [ ] Re-snapshot-after-DOM-change rule + `--headed` daemon-reuse gotcha carried forward
- [ ] The connect-to-running-app path (`--cdp <port>` / `--auto-connect`) is surfaced as the **Chromium-desktop (Electron / WebView2) driver**, not just "connect to Chrome" (`references/advanced.md` already documents "control Electron apps … WebView2 apps")
- [ ] SKILL.md ladder pointer for the default rung resolves to this reference

## Done summary
Created references/agent-browser.md as the default web-rung entry point — folds the 7 existing agent-browser references into an index and carries forward content that lived only in the old single-driver SKILL.md (command chaining/daemon persistence, --headed daemon-reuse gotcha + pkill/macOS-activate recipes, setup/version check, config file, local files), surfacing the --cdp/--auto-connect path as the Chromium-desktop (Electron/WebView2) CDP driver. Resolved SKILL.md's default-rung pointer to it and dropped the temporary placeholder note. No capability regression: all 44 subcommands + 31 flags from the old skill remain reachable.
## Evidence
- Commits: 559bbe143fcdaf9f823f5c2e71162c4e97caac96
- Tests: smoke: references/agent-browser.md exists + SKILL.md default-rung pointer resolves to it (SKILL.md line 52 rung-1 cell + line 60 note), smoke: all 7 folded reference links from agent-browser.md resolve, no dangling (the 4 remaining SKILL.md rung links chrome-devtools-mcp/playwright/cursor-ide-browser/computer-use are fn-51.3/.4 scope, not this task), no-regression: 44/44 old-SKILL.md subcommands + 31/31 global flags reachable in new rung surface (agent-browser.md + 7 refs), no-regression: all 19 old-SKILL.md sections + 17 task-required specifics present (re-snapshot rule, --headed daemon-reuse gotcha, pkill recipe, macOS activate, --cdp/--auto-connect Chromium-desktop driver, Electron/WebView2 framing, command chaining, doctor/install, --session-name, encryption, config file, local files, annotate, iOS), verified against installed agent-browser 0.27.0: doctor/install/upgrade/skills-get-core-full/skills-get-electron/--auto-connect all confirmed present
- PRs:
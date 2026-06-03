---
satisfies: [R1, R3]
---

## Description
Rename the `browser` skill to `flow-next-drive` and rewrite SKILL.md from a single-driver reference into a **lean router**. This is the early-proof task: it establishes the progressive-disclosure structure everything else hangs off.

`git mv plugins/flow-next/skills/browser plugins/flow-next/skills/flow-next-drive`; set frontmatter `name: flow-next-drive`; write a description carrying web+native triggers, kept under ~1000 ASCII bytes (Codex 1024-**byte** limit — no em-dashes/smart-quotes/emoji).

SKILL.md becomes the router ONLY: (1) **surface detection** — classify into web app / Chromium-backed desktop app (Electron/WebView2 → web ladder by CDP-attach to the app's debug port) / true-native or non-CDP surface (AppKit/SwiftUI, or macOS WKWebView/Tauri-on-macOS → Computer Use) and branch; (2) the shared **universal flow** (observe/navigate → snapshot → act on fresh refs → capture evidence → release); (3) the **driver-ladder table** (web rungs in order + the native rung); (4) **driver-detection / graceful-degradation** logic (probe availability, pick highest rung that passes, fail soft to the next, terminal rung = manual; never hard-depend; Computer Use never on a headless/CI path); (5) **per-rung pointers** with explicit trigger conditions ("For attach-to-real-Chrome / Lighthouse → read references/chrome-devtools-mcp.md"). Extract ALL agent-browser command detail OUT of SKILL.md (it lands in fn-51.2's rung reference).

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-drive/SKILL.md (+ dir rename via git mv)

## Approach
- Use Pattern B (references/ subdir) — it's already the skill's layout. Model the lean-SKILL.md + imperative `Read references/<x>.md` pattern on `flow-next-strategy/SKILL.md` and `flow-next-capture/SKILL.md`.
- One hop from SKILL.md, never nested. Give each pointer a trigger condition, not a bare link.
- Mirror Ray's ladder structure (browser-playbook.md / computer-use-playbook.md) rather than inventing one.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/browser/SKILL.md` (currently 454 lines — extract agent-browser specifics out; this is a net extraction)
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md` + `references/` — progressive-disclosure exemplar (references/ subdir + imperative Read)
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — lean-router + sibling-doc pattern
- `CLAUDE.md:55-64` — cross-platform patterns (canonical Claude-native names; AskUserQuestion/Task rewrite rules if the router prompts for rung choice)
- `~/repos/rayfernando-skills/.../references/browser-playbook.md` + `computer-use-playbook.md` — ladder + universal-flow structure to mirror (Apache-2.0)

## Acceptance
- [ ] Directory renamed `skills/browser` → `skills/flow-next-drive`; frontmatter `name: flow-next-drive`
- [ ] SKILL.md is a router well under the ~500-line cap (no agent-browser command dump inline)
- [ ] Surface-detection conditional present, 3-way: web app / Chromium-desktop (Electron/WebView2 → web ladder via CDP) / true-native or non-CDP webview (→ Computer Use)
- [ ] Universal flow + driver-ladder table (all rungs, in order) + driver-detection/graceful-degradation logic present
- [ ] Per-rung pointers carry explicit trigger conditions, one hop, not nested
- [ ] `description` < 1000 ASCII bytes, no non-ASCII punctuation; carries web + native triggers
- [ ] Skill loads on Claude (smoke); if rung-choice prompting is added it uses bare `AskUserQuestion` + declares `allowed-tools`

## Done summary
Renamed the `browser` skill to `flow-next-drive` (git mv, references preserved R100) and rewrote SKILL.md from a 454-line agent-browser command reference into an 84-line surface-aware router: 3-way surface detection (web app / Chromium-desktop via CDP / true-native via Computer Use), a shared universal flow, the web driver ladder + native Computer Use rung, driver-detection/graceful-degradation logic, and per-rung pointers with explicit trigger conditions. All agent-browser command detail was extracted out (lands in fn-51.2's rung reference); description is 823 ASCII bytes under the Codex 1024-byte limit.
## Evidence
- Commits: 63e480286489e482b9e63f842b218968fe7b1924
- Tests: ls plugins/flow-next/skills/flow-next-drive/SKILL.md -> exists (S1 PASS), grep -m1 '^name:' SKILL.md -> name: flow-next-drive (S2 PASS), wc -l SKILL.md -> 84 lines, well under ~500 cap (S3 PASS), grep stray 'browser' skill-name refs in skills/ -> 0 (S4 PASS); sync-codex.sh 3 residual 'browser' refs DEFERRED to fn-51.5 per spec R2/R7, description byte count -> 823 bytes < 1000/1024 Codex limit, clean ASCII no non-ASCII punctuation (S5 PASS), 3-way surface conditional: Web app / Chromium-backed desktop (Electron/WebView2 via CDP) / True-native non-CDP (WKWebView -> Computer Use) all present (S6 PASS), universal flow block observe->snapshot->act->verify->capture->release present (S7 PASS), driver-ladder table all 5 rungs in order: agent-browser -> chrome-devtools-mcp -> Playwright -> cursor-ide-browser -> manual (S8 PASS), per-rung pointers: 6 distinct references/<x>.md one-hop pointers with explicit trigger conditions in 'Use when' column (S9 PASS), agent-browser command detail extracted: 0 inline command dumps; explicit pointer that detail lands in fn-51.2 references/agent-browser.md (S10 PASS), markdown table column-count consistency: 2 tables, all consistent (S11 PASS), interim agent-browser reference targets (commands/advanced/auth/snapshot-refs/session-management/debugging .md) all resolve -> no regression (S12 PASS), git rename preserved reference history: 7 R100 renames (S13 PASS), python3 YAML frontmatter parse: name=flow-next-drive, desc 823 ASCII bytes (PASS)
- PRs:
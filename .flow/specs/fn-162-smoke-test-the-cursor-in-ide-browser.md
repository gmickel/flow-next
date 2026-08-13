# Smoke-test the Cursor in-IDE browser rung for drive/QA

> **STATUS: LIVE-PASS RECORDED (2026-08-13).** Rung 4 drives; it was documented wrong. R6 demotion is **not** the outcome. R3 (console + network from the driven surface) remains unresolved — a QA pass on this rung records an evidence gap, not PASS. Per-step table: [`.flow/artifacts/fn-162/live-pass.md`](../artifacts/fn-162/live-pass.md).

## Overview

`flow-next-drive` ships **rung 4 — `cursor-ide-browser`**: Cursor's built-in in-IDE browser, exposed as the `cursor-ide-browser` MCP. It was authored from public docs and never driven. A 2026-08-13 live pass inside Cursor showed the rung **works** (snapshot YAML, real screenshots, lock, 16-tool surface) and that the old reference was fiction in the ways that made it look broken: catalog omission was treated as absence, `browser_console_messages` does not exist, `browser_select_option` was missing from the inventory, and the flake is an MCP-level unregister, not garbage snapshots.

`/flow-next:qa` still cannot green-light a pass on this rung: console + network were not captured from the driven surface (MCP dropped before those channels; there is no console MCP tool). The corrected reference + ladder row carry that evidence-gap caveat. Host dependence is unchanged — off Cursor the rung is absent and the ladder falls through.

## Quick commands

Rung 4 has no automated suite — it is an in-IDE MCP surface, so the smoke test is a **manual scripted pass run inside Cursor**, with evidence captured to `.flow/artifacts/`. The only automated surface is the doc/mirror gate:

```bash
./scripts/sync-codex.sh   # twice, idempotency — the reference file is mirrored
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

## Goal & Context
<!-- scope: business -->

A rung on the drive ladder that has never been exercised is a liability: it tells the agent "this path exists" and the agent will route to it on a Cursor host when `agent-browser` is unavailable. If it can't actually deliver console + network evidence, `/flow-next:qa` either fails confusingly mid-pass or — worse — passes on DOM-only evidence, which the QA skill explicitly forbids.

Two things drive urgency:

1. **Cursor is a first-class host** (`.cursor-plugin/marketplace.json`, `install-cursor.sh`) and gets **no rewrite pass** — canonical prose reaches Cursor users verbatim. Wrong tool names there are wrong in production.
2. **A specific documented gap:** upstream says browser **network traffic is "only available in the Agent panel"**. If that means network inspection is unreachable from the tool surface the agent drives, rung 4 structurally cannot satisfy the drive `verify` contract, and the rung's write-up is currently misleading by omission.

## Architecture & Data Models
<!-- scope: technical -->

Files in play (canonical only; the Codex mirror is regenerated, never hand-edited):

- `plugins/flow-next/skills/flow-next-drive/references/cursor-ide-browser.md` — the rung reference; the artifact this spec corrects.
- `plugins/flow-next/skills/flow-next-drive/SKILL.md` — Step 3 ladder table row for rung 4, and the `verify`-is-not-DOM-only contract in Step 2.
- `plugins/flow-next/skills/flow-next-qa/SKILL.md` — consumer; its verdict depends on the evidence this rung can or cannot produce.
- `plugins/flow-next/docs/platforms.md` — where host-behavior differences are recorded.
- `plugins/flow-next/codex/skills/flow-next-drive/**` — mirror, via `./scripts/sync-codex.sh` (run twice).

**The smoke test is a scripted universal-flow pass**, run inside Cursor. The planned target was a trivial local page with a button, a deliberate `console.error`, and a `fetch()` to a 500 endpoint. The executed pass used the flowmeter dashboard at `http://127.0.0.1:8788/` (already open) plus a follow-up attach in this repo. Console.error + 500 were **not** exercised — the MCP dropped first. That is recorded as R3 unresolved, not as a pass.

```
observe   browser_tabs list
navigate  browser_navigate <local url>
lock      browser_lock (if the tool exists as documented)
snapshot  browser_snapshot → refs
act       browser_click / browser_fill / browser_select_option on a known control
verify    console + network — no MCP tool; CDP Log.enable / Network.enable not live-tested
capture   browser_take_screenshot   → real image reached the agent
release   unlock / close — MCP drop can leave a locked tab (Take Control)
```

Each step yields one of three verdicts: **works as documented** / **works differently** (record actual shape) / **absent**. The table lives at `.flow/artifacts/fn-162/live-pass.md`.

### Live pass (2026-08-13) — settled vs still open

Primary source of truth is Cursor's host cache (outside git, version-matched, appears after first use): `~/.cursor/projects/<workspace-slug>/mcps/cursor-ide-browser/` (`INSTRUCTIONS.md` + 16 `tools/*.json`). Secondary: <https://cursor.com/docs/agent/tools/browser> (fetched 2026-08-13).

**Settled (R2, most of R1, R4, R5, not-R6):** 16 live tools; no `browser_console_messages`; `browser_select_option {ref, values[]}` required for `<select>`; `viewId` on every tool except `browser_tabs` (targets by `index`); `browser_cdp` real including `Input.*` denied; lock-first when a tab already exists; omit `position` for background navigate; snapshot YAML + opaque refs; real screenshots; catalog omit is not absence (id-probe attaches); flake is MCP unregister mid-run; re-probe restored the server 0 times after a drop; interactive-IDE-only; Manual approval blocks unattended use.

**Still open (R3):** console + network from the driven surface. Public docs say logs go to files the agent greps, and network is "Agent panel only." Cursor's `INSTRUCTIONS.md` lists `Log.enable` / `Network.enable` as CDP examples — that is not live evidence. Do not claim either channel works.

### Documentation dossier (gathered 2026-08-03, pre-implementation — historical)

Canonical: <https://cursor.com/docs/agent/tools/browser>. Everything below was from upstream docs, not from a live run — retained as the pre-pass input. The live pass superseded the tool-inventory and CDP questions.

- **Mechanism.** Native to Cursor, no external install. Runs as an extension exposing a **secure web view controlled via an MCP server**. Per-session random token auth; each tab gets a random id; browser context **isolated per workspace**, with cookies / `localStorage` / `sessionStorage` / IndexedDB persisting per workspace.
- **Pre-pass inventory delta (settled).** Upstream described 6–7 capabilities by function. The old reference claimed 11 `browser_*` tools including the nonexistent `browser_console_messages`. Live inventory is 16; see the artifact.
- **Console evidence.** Logs are **written to files that Agent can grep and selectively read** (public docs 2026-08-13). There is no `browser_console_messages` tool. Grep-a-file vs CDP `Log.enable` was **not live-tested**.
- **Network evidence.** Public docs (2026-08-13): **"currently only available in the Agent panel, coming soon to the layout."** Not live-tested from the driven surface.
- **Screenshots** are wired into the file-reading tool so the agent sees real images — **confirmed live**.
- **Approval model.** Browser tools require approval by default; three modes — **Manual approval** (recommended) / **allow-listed actions** / **Auto-run**. Configured at **Settings → Agents → Auto-Run**. Upstream calls the guardrails "best-effort" and warns explicitly against Auto-run on untrusted code or unfamiliar sites (prompt-injection).
- **Enterprise origin allowlist (v2.1+).** Restricts `browser_navigate` destinations and gates MCP tool execution by origin. Documented bypasses: link clicks from an allowed origin to a non-allowed one succeed, allowed→non-allowed redirects are permitted, and JavaScript-based navigation bypasses the restriction. Manual navigation stays unrestricted while tools stay blocked on non-allowed origins.
- **No CLI / headless path is documented.** Nothing in the Browser page or the CLI docs indicates `cursor-agent` can drive it; it reads as Agent-panel/IDE-pane only.
- **CDP surface.** Public docs mention none. Cursor's host-cache `INSTRUCTIONS.md` and `browser_cdp.json` document it, including `Input.*` denied. Schema-confirmed 2026-08-13; not exercised beyond existence.
- **Version context.** Cursor 3 (2026-04-02) rebuilt the UI around agents; the 3.2 point release added **screenshot-based browser-automation clicking**. Snapshot YAML + opaque refs remain the action model; screenshot is a separate vision path.
- **Upstream model recommendation** for browser work: Sonnet 4.5, GPT-5, or Auto. Note for our routing table: it is *their* recommendation for *their* harness, not a flow-next routing claim.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A scripted smoke pass is executed **inside a real Cursor IDE session** over the full universal flow (observe → navigate → snapshot → act → verify → capture → release) against a local target that deliberately emits a `console.error` **and** a failing (500) API request. Result recorded per step as works-as-documented / works-differently / absent, with the actual tool name and parameter shape captured for every step that differs. Evidence (screenshot + console excerpt + whatever network output exists) is attached to the spec; a pass claimed from reading docs is not acceptance.
- **R2:** The tool inventory in `references/cursor-ide-browser.md` matches the **live** MCP tool list. Every name and parameter our reference asserts beyond upstream's documented set (`browser_lock`, `browser_snapshot`, `browser_fill`, `browser_press_key`, `browser_highlight`, `browser_cdp`, the `viewId` parameter) is either confirmed live or removed. No name survives on the strength of "it was in the file already."
- **R3:** The **console** and **network** evidence channels get a definitive verdict. If network inspection is unreachable from the driven tool surface (the upstream "Agent panel only" note), the reference says so plainly and the SKILL.md rung-4 row carries the consequence: rung 4 **cannot** satisfy the drive `verify` contract unaided, and a QA pass routed to it must record a documented evidence gap rather than a PASS. Console shape is documented as it actually behaves (grep-a-file vs inline return).
- **R4:** Host dependence and the absence of a CLI/headless path are stated explicitly: rung 4 is reachable **only** from an interactive Cursor IDE session — not from `cursor-agent`, not from CI, never on a headless path. The existing detect-never-depend contract and the fall-through to manual are preserved verbatim.
- **R5:** The approval model is documented as an **operator precondition**, not a footnote: with default Manual approval every browser action blocks on a human click, so an autonomous `/flow-next:qa` or pilot pass on this rung stalls. The reference states which mode is required for an unattended pass and repeats upstream's warning against Auto-run on untrusted origins. The enterprise origin allowlist and its three documented bypasses are recorded.
- **R6:** If the live pass shows the rung is too flaky or too gapped to route to at all, the accepted outcome is a **demotion**: rung 4 becomes a documented limitation (or moves below manual relay) with the failing evidence recorded in the reference. A rung that cannot produce evidence must not stay advertised as a rung — "it didn't work" is a valid result of this spec, not a failure of it.
- **R7:** Canonical + mirror stay in lockstep: `./scripts/sync-codex.sh` run twice is byte-idempotent, the mirror diff is committed with the canonical change, and `plugins/flow-next/docs/platforms.md` records the Cursor-host behavior difference. `test_prompt_text_pinned` is updated in the same commit if a pinned prompt changes, with the rationale in the commit message.
- **R8:** Every fact written into the reference is traceable to either the live smoke pass or a dated upstream doc URL. The "Drift-prone facts — verify at build" block is either resolved and removed, or narrowed to what genuinely remains unverifiable — it does not survive unchanged.

## Boundaries
<!-- scope: business -->

- **No new rung, no new driver.** Rung 4 exists; this verifies, corrects, or demotes it.
- **No changes to rungs 1–3** (`agent-browser`, `chrome-devtools-mcp`, Playwright) or the native rung (Cua / Computer Use).
- **No portability work.** Making the Cursor browser reachable off the Cursor IDE is explicitly out of scope; the rung stays host-dependent.
- **No flowctl code.** Documentation, skill prose, and the mirror only — flowctl never imports a driver.
- **No automated test harness for the rung.** It's an interactive in-IDE MCP surface; a CI test for it would be theater. The smoke pass is manual and evidenced.
- **Not a QA-skill redesign.** If rung 4 can't meet the verify contract, the fix here is to say so, not to relax the contract.

## Decision Context
<!-- scope: both -->

**Why a smoke test rather than deleting the rung.** On a Cursor host with no `agent-browser` install, rung 4 may be the only automated path to UI evidence. Deleting it unverified throws away a real capability; keeping it unverified ships instructions that may be fiction. One live pass resolves which.

**Why "it doesn't work" is an acceptable outcome (R6).** The value is a truthful ladder. A documented limitation the agent can plan around beats a rung that fails halfway through a QA pass and leaves a half-driven session behind. **2026-08-13: R6 not taken** — the rung drives; the docs were wrong.

**Why the network channel is the crux.** flow-next's drive/QA contract treats a green DOM over a failed API call as a **finding, not a pass**. A rung that cannot see network traffic cannot support that contract, however well it clicks. That single question decides whether rung 4 is a QA-capable rung or only a look-at-the-page convenience. **2026-08-13: still unanswered from the driven surface** — evidence gap, not PASS.

**Why the approval model is acceptance-level and not a note.** Default Manual approval makes an unattended pass impossible. A rung documented as available but silently attended-only would break exactly the autonomous flows (pilot, `pipeline.qa`) that would reach for it.

## Open questions (settle at interview or in the live pass)

1. Do the 11 `browser_*` tools in our reference actually exist, and is `viewId` the real parameter name? **SETTLED 2026-08-13:** 16 tools; `viewId` real on all except `browser_tabs` (targets by `index`).
2. Is network traffic reachable from the driven tool surface, or Agent-panel-only? **UNRESOLVED** — dedicated smoke at `http://127.0.0.1:8762/` (fetch → 500) never loaded; MCP dropped after lock, before `Network.enable`. Public docs still say Agent-panel-only. Treat as unreachable for QA until a live capture exists.
3. Does `browser_cdp` exist? If yes, is the `Input.*`-focus caveat in our reference real or inherited folklore? **SETTLED 2026-08-13:** tool exists; `Input.*` denied in Cursor's own `INSTRUCTIONS.md` + `browser_cdp.json` (schema-confirmed, not executed).
4. Console: inline return or grep-a-log-file? **UNRESOLVED** — no `browser_console_messages` tool. Dedicated smoke (`console.error` on load) never loaded; `Log.enable` never returned. Public docs say grep-a-file.
5. Which Auto-Run mode is the minimum for an unattended pass, and are we willing to recommend it at all given the prompt-injection warning? **SETTLED from dated docs (2026-08-13):** allow-listed or Auto-run required; Manual blocks unattended use; do not recommend Auto-run on untrusted origins.
6. Did Cursor 3.2's screenshot-based clicking change the ref/snapshot model the reference describes? **SETTLED 2026-08-13:** snapshot YAML + opaque refs remain the action model; screenshot is a separate vision path (`browser_take_screenshot`).
7. Who runs the live pass — it requires an interactive Cursor IDE on this machine, which no other flow-next task needs. **SETTLED:** maintainer, 2026-08-13, plus a follow-up attach in this repo the same day.

## References

- `.flow/artifacts/fn-162/live-pass.md` (per-step verdict table)
- `plugins/flow-next/skills/flow-next-drive/references/cursor-ide-browser.md` (rung 4 reference — the artifact under test)
- `plugins/flow-next/skills/flow-next-drive/SKILL.md` Step 2 (verify contract), Step 3 (ladder table, rung 4 row)
- `plugins/flow-next/skills/flow-next-qa/SKILL.md` (consumer; `qa_verdict` evidence rules)
- `plugins/flow-next/docs/platforms.md` (host-behavior notes)
- `.flow/specs/fn-51-flow-next-drive-surface-aware-ui.md`, `.flow/specs/fn-53-flow-nextqa-live-app-real-user-qa-pass.md` (origin of the ladder and the QA verdict contract)
- Upstream, Cursor browser tool: <https://cursor.com/docs/agent/tools/browser>
- Upstream, Cursor CLI overview (no browser tool documented): <https://cursor.com/docs/cli/overview>
- Upstream, Cursor 3 announcement (agent-first redesign, 2026-04-02): <https://cursor.com/blog/cursor-3>
- Upstream, Cursor changelog (no browser entries through 2026-07-29): <https://cursor.com/changelog>

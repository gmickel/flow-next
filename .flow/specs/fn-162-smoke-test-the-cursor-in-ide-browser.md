# Smoke-test the Cursor in-IDE browser rung for drive/QA

> **STATUS: STUB.** Captured urgently to hold the shape and the doc dossier. The acceptance criteria below are written to be verifiable, but several facts marked **[VERIFY-LIVE]** can only be settled by running the rung inside a real Cursor IDE session — that live pass is the point of the spec, not a prerequisite for it. Interview/plan before working.

## Overview

`flow-next-drive` already ships **rung 4 — `cursor-ide-browser`**: Cursor's built-in in-IDE browser, exposed to the agent as `browser_*` MCP tools. It was authored from Cursor's public docs and never driven for real. Its own reference file admits this in a "Drift-prone facts — **verify at build**" section: the tool names, the `viewId` parameter shape, and the Auto-Run approval modes are unconfirmed.

That is a hole in the QA chain. `/flow-next:qa` refuses to green-light a pass on narration — its `qa_verdict` rests on captured evidence (DOM state **plus** clean console **plus** no failed API request). Rung 4 is a documented path to that evidence on the one host where the higher rungs may be missing, and nobody has ever proven it can produce it.

This spec is a **smoke test plus documentation-truthing pass**, not a feature. Output: a live-verified rung reference, or a demotion of rung 4 to a documented limitation with the reason recorded.

**Host dependence is known and accepted.** The rung exists only inside the Cursor IDE. Off Cursor (Claude Code / Codex / Droid terminals, cloud VMs, CI) it is simply absent and the ladder falls through — the existing "detect, never depend" contract stays exactly as-is. This spec does not try to make it portable.

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

**The smoke test is a scripted universal-flow pass**, run inside Cursor against a trivial local target (a `python3 -m http.server` page with a button, a deliberate `console.error`, and a `fetch()` to a 500 endpoint — enough to prove all three evidence channels at once):

```
observe   browser_tabs list
navigate  browser_navigate <local url>
lock      browser_lock (if the tool exists as documented)
snapshot  browser_snapshot → refs
act       browser_click / browser_fill on a known control
verify    browser_console_messages  → is the deliberate console.error visible?
          network                   → is the deliberate 500 visible at all? by what tool?
capture   browser_take_screenshot   → does a real image reach the agent?
release   unlock / close
```

Each step yields one of three verdicts: **works as documented** / **works differently** (record actual shape) / **absent**. The deliverable is that table plus the corrected reference.

### Documentation dossier (gathered 2026-08-03, pre-implementation)

Canonical: <https://cursor.com/docs/agent/tools/browser>. Everything below is from upstream docs, not from a live run — all of it is **[VERIFY-LIVE]** input, not settled fact.

- **Mechanism.** Native to Cursor, no external install. Runs as an extension exposing a **secure web view controlled via an MCP server**. Per-session random token auth; each tab gets a random id; browser context **isolated per workspace**, with cookies / `localStorage` / `sessionStorage` / IndexedDB persisting per workspace.
- **Documented capability set (6–7 tools).** `browser_navigate` is the only name upstream spells out. The rest are described by function: click (incl. double/right-click, hover), type, scroll, screenshot, console output, network traffic. **Our reference file claims 11 `browser_*` tools** (`browser_tabs`, `browser_lock`, `browser_snapshot`, `browser_click`, `browser_fill`, `browser_press_key`, `browser_scroll`, `browser_console_messages`, `browser_take_screenshot`, `browser_cdp`, `browser_highlight`) — a superset of anything upstream documents. That delta is the single biggest thing to settle.
- **Console evidence.** Logs are **written to files the agent greps and selectively reads**, deliberately not summarized after each action. Our reference implies a `browser_console_messages` call returns them inline. Different shape → different instructions.
- **Network evidence.** Monitors requests, payloads, status codes — but **"currently only available in the Agent panel, coming soon to the layout."** Directly threatens the drive `verify` contract.
- **Screenshots** are wired into the file-reading tool so the agent sees real images, not text descriptions.
- **Approval model.** Browser tools require approval by default; three modes — **Manual approval** (recommended) / **allow-listed actions** / **Auto-run**. Configured at **Settings → Agents → Auto-Run**. Upstream calls the guardrails "best-effort" and warns explicitly against Auto-run on untrusted code or unfamiliar sites (prompt-injection).
- **Enterprise origin allowlist (v2.1+).** Restricts `browser_navigate` destinations and gates MCP tool execution by origin. Documented bypasses: link clicks from an allowed origin to a non-allowed one succeed, allowed→non-allowed redirects are permitted, and JavaScript-based navigation bypasses the restriction. Manual navigation stays unrestricted while tools stay blocked on non-allowed origins.
- **No CLI / headless path is documented.** Nothing in the Browser page or the CLI docs indicates `cursor-agent` can drive it; it reads as Agent-panel/IDE-pane only. This matters twice over — the rung can't be exercised from our `cursor-agent` bridges (`review.backend cursor:*`, the implementation bridge), and it can never serve a headless/CI QA pass.
- **No CDP surface is documented.** Our reference exposes `browser_cdp` as a raw escape hatch (with an `Input.*`-is-broken caveat). Upstream mentions no CDP at all. Verify or delete — a fabricated escape hatch is worse than none.
- **Version context.** Cursor 3 (2026-04-02) rebuilt the UI around agents; the 3.2 point release added **screenshot-based browser-automation clicking** and an Await tool for background runs; Design Mode annotates browser UI to feed visual feedback back to an agent. The public changelog through 2026-07-29 (iPad, Start plan, Router, 3.11 Side Chats) carries **no** browser entries, so the browser surface has been quiet for ~4 months — the docs page is the live reference.
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

**Why "it doesn't work" is an acceptable outcome (R6).** The value is a truthful ladder. A documented limitation the agent can plan around beats a rung that fails halfway through a QA pass and leaves a half-driven session behind.

**Why the network channel is the crux.** flow-next's drive/QA contract treats a green DOM over a failed API call as a **finding, not a pass**. A rung that cannot see network traffic cannot support that contract, however well it clicks. That single question decides whether rung 4 is a QA-capable rung or only a look-at-the-page convenience.

**Why the approval model is acceptance-level and not a note.** Default Manual approval makes an unattended pass impossible. A rung documented as available but silently attended-only would break exactly the autonomous flows (pilot, `pipeline.qa`) that would reach for it.

## Open questions (settle at interview or in the live pass)

1. Do the 11 `browser_*` tools in our reference actually exist, and is `viewId` the real parameter name? **[VERIFY-LIVE]**
2. Is network traffic reachable from the driven tool surface, or Agent-panel-only? **[VERIFY-LIVE]** — decides R3 and effectively R6.
3. Does `browser_cdp` exist? If yes, is the `Input.*`-focus caveat in our reference real or inherited folklore? **[VERIFY-LIVE]**
4. Console: inline return or grep-a-log-file? **[VERIFY-LIVE]**
5. Which Auto-Run mode is the minimum for an unattended pass, and are we willing to recommend it at all given the prompt-injection warning?
6. Did Cursor 3.2's screenshot-based clicking change the ref/snapshot model the reference describes?
7. Who runs the live pass — it requires an interactive Cursor IDE on this machine, which no other flow-next task needs.

## References

- `plugins/flow-next/skills/flow-next-drive/references/cursor-ide-browser.md` (rung 4 reference — the artifact under test)
- `plugins/flow-next/skills/flow-next-drive/SKILL.md` Step 2 (verify contract), Step 3 (ladder table, rung 4 row)
- `plugins/flow-next/skills/flow-next-qa/SKILL.md` (consumer; `qa_verdict` evidence rules)
- `plugins/flow-next/docs/platforms.md` (host-behavior notes; already mentions the rung)
- `.flow/specs/fn-51-flow-next-drive-surface-aware-ui.md`, `.flow/specs/fn-53-flow-nextqa-live-app-real-user-qa-pass.md` (origin of the ladder and the QA verdict contract)
- Upstream, Cursor browser tool: <https://cursor.com/docs/agent/tools/browser>
- Upstream, Cursor CLI overview (no browser tool documented): <https://cursor.com/docs/cli/overview>
- Upstream, Cursor 3 announcement (agent-first redesign, 2026-04-02): <https://cursor.com/blog/cursor-3>
- Upstream, Cursor changelog (no browser entries through 2026-07-29): <https://cursor.com/changelog>

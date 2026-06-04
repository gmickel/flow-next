---
satisfies: [R1, R3, R4]
---

## Description
Add the **single value-checked gate** to the work skill (zero default-path bloat) and the **host-side pre-flight gates + one-time consent**, plus scaffold the new reference doc. With delegation off, `/flow-next:work` stays byte-identical — exactly one cheap value-check. When active, the host (not the worker subagent) runs the gates + consent once, before the per-task loop, and passes the resolved flags into each spawned worker.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/SKILL.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` (new — scaffold + pre-flight section)

## Approach
- Mirror the tracker-sync touchpoint shape (`SKILL.md:144-153`, `phases.md:99-107`/`:154-162`): a cheap `flowctl config get work.delegate --json | jq` value-check computing `delegation_active` ONCE pre-loop, then a one-line `# read references/codex-delegation.md` pointer. Default path = the single jq check, no new steps.
- **Activation is disambiguated from the review backend.** `/flow-next:work` already maps generic "use codex" to the review backend. Delegation activates only on `delegate:codex` (off: `delegate:local`), `work.delegate=codex`, or an explicit "use codex **for implementation**" phrase — never bare "use codex".
- **Original-input-kind capture (load-bearing, conditional):** `phases.md` Phase 1 promotes a bare idea into a spec+task, so the input-kind gate must read the ORIGINAL input *before* Phase 1 runs. But set `INPUT_WAS_BARE_PROMPT` ONLY when `delegation_active` is already true (it runs after the cheap value-check) — the default (delegation-off) path must stay a single `config get` step. A promoted bare prompt is NOT eligible for delegation.
- **Consent lives in the host work skill** (`SKILL.md`/`phases.md`), NOT `worker.md` — the worker is a subagent and can't call `AskUserQuestion` (#12890/#34592). Lead-with-recommendation + persist-on-confirmation pattern from tracker-sync (`SKILL.md:62-67`, `steps.md:35-53`); `ToolSearch select:AskUserQuestion` first.
- Host pre-flight gates (run once, any failure → standard mode): (1) **platform = Claude Code only** — pin the exact probe at build: enable ONLY when the `CLAUDECODE` env marker is present AND `DROID_PLUGIN_ROOT` unset (Droid exposes `CLAUDE_PLUGIN_ROOT` as a compat alias, so don't key on that) AND no OpenCode marker. Do NOT exclude on `CODEX_*` — `CODEX_SANDBOX=auto` is flow-next's review-backend knob (Ralph exports it), not a Codex-orchestrator signal; the inside-codex case is gate (2), the recursion guard; (2) recursion guard — trip on a Codex RUNTIME `CODEX_SANDBOX` value (outside the flow-next config set `{read-only,workspace-write,danger-full-access,auto}`, e.g. `seatbelt`) or `$CODEX_SANDBOX_NETWORK_DISABLED`; do NOT trip on the bare presence of `$CODEX_SANDBOX` (Ralph exports `CODEX_SANDBOX=auto` as a review-backend knob — flowctl `CODEX_SANDBOX_MODES` — so a naive check disables delegation in every Ralph run). Pin the exact runtime value(s) at build; (3) `command -v codex`; (4) one-time consent → persist `work.delegateConsent`/`work.delegateSandbox`; (5) original input is plan/spec/task (per `INPUT_WAS_BARE_PROMPT`). Headless (Ralph): proceed only if `work.delegateConsent` already `true`, else off silently.
- **`work.delegateDecision` behavior:** `auto` (default) → delegate every eligible task without a per-task prompt; `ask` → in interactive mode the host asks (AskUserQuestion) before delegating each task. Headless treats `ask` as `auto` only when consent already granted.
- Pass resolved flags (delegate on/off, sandbox, effort floor, decision) into the worker prompt where `phases.md:131` injects worker context.
- Scaffold `references/codex-delegation.md` with the pre-flight section authored; invocation/safety/ralph sections filled by fn-55.3–.5. Follow the tracker-sync `references/*.md` house style.

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-work/SKILL.md:132-159` — tracker-sync progressive-disclosure prose block (the shape to mirror) + the existing "use codex" review-backend option parsing (disambiguation)
- `plugins/flow-next/skills/flow-next-work/phases.md:1-137` — Phase 1 input promotion (capture point) + Phase 3c "Spawn Worker" (flag-passing)
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md:62-67` + `steps.md:35-53` — consent ceremony (AskUserQuestion → persist on confirmation)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/` — reference-doc house style
**Optional**:
- `plugins/flow-next/scripts/flowctl.py:17802` `cmd_codex_check` — availability-probe precedent (`shutil.which`)

## Acceptance
- [ ] With `work.delegate=false` (default), a diff of `phases.md`/`SKILL.md` shows the default execution path adds exactly ONE value-check (`flowctl config get work.delegate`) and no other behavioral step — default `/flow-next:work` is byte-identical to before.
- [ ] Activation triggers on `delegate:codex` / `work.delegate=codex` / "use codex for implementation" but NOT on the generic "use codex" (which still selects the review backend).
- [ ] When `delegation_active`, the host reads `references/codex-delegation.md` (one-line pointer present) and runs the pre-flight gates once before the per-task loop.
- [ ] The input-kind gate runs ONLY when `delegation_active`, evaluated on the ORIGINAL input before Phase 1 promotion (`INPUT_WAS_BARE_PROMPT`); a bare prompt promoted to a spec is NOT eligible; the default (delegation-off) path adds no input-kind step.
- [ ] The platform gate keys on the `CLAUDECODE` marker with exclusions for `DROID_PLUGIN_ROOT` + OpenCode (NOT `CODEX_*`), pinned/verified at build; a test confirms delegation stays eligible when `CODEX_SANDBOX=auto` is exported (the Ralph case).
- [ ] The recursion guard trips on a Codex-runtime `CODEX_SANDBOX` value or `$CODEX_SANDBOX_NETWORK_DISABLED` but NOT on `CODEX_SANDBOX=auto` (the Ralph review-backend knob) — verified by a test that delegation stays eligible when `CODEX_SANDBOX=auto` is exported. No `$CODEX_SESSION_ID`.
- [ ] One-time consent is issued from the host skill via `AskUserQuestion` and persists `work.delegateConsent`/`work.delegateSandbox`; a second run with consent already `true` does not re-prompt.
- [ ] `work.delegateDecision=ask` makes the host ask before each delegated task (interactive); `auto` does not. Headless: `ask`→`auto` only when consent pre-granted.
- [ ] Headless/Ralph (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set): no `AskUserQuestion`; delegation proceeds only if `work.delegateConsent` already `true`, else silently off.
- [ ] `references/codex-delegation.md` exists with the pre-flight section authored + section stubs for invocation/safety/ralph.

## Done summary
_(pending implementation)_

## Evidence
_(pending implementation)_

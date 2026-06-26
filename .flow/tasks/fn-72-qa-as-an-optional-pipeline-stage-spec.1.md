---
satisfies: [R2, R4, R5]
---

## Description

Make `/flow-next:qa` **evidence-aware**, **autonomous-safe**, and extend its `qa_verdict` receipt with the lean fields the pilot stage + make-pr depend on. Extends the QA skill's mode detection, `derive` phase, and receipt writer. **Lean + agentic: NO new flowctl subcommand, NO persisted `.flow/qa/` artifact, NO new receipt** — the host derives + drives in-context; the only persisted output stays the (now richer) `qa_verdict`. Reusable by user-invoked QA too (the early proof point).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-qa/SKILL.md` (mode detection + framing), `plugins/flow-next/skills/flow-next-qa/workflow.md` (derive phase + receipt writer)

## Approach

- **Autonomous-mode detection at the PREAMBLE (not post-verdict):** the QA workflow prompts in its early phases, so autonomous detection must be parsed/exported in `SKILL.md` mode-detection and consumed from the workflow **preamble / first phase**, *before any prompt path* — not in the post-verdict preflight. Parse a `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env signal (same shape as plan's autonomous branch). Under autonomous: **ask NO questions**; an undocumented target URL / required accounts / missing local app ⇒ emit a `BLOCKED` `qa_verdict` + clean exit, **never** an interactive prompt (so the pilot stage can't hang). Autonomy ≠ Ralph (no ralph-guard hooks).
- **Evidence-aware subtraction — insertion point:** the `derive` phase, `flow-next-qa/workflow.md:144-190`, hooked **before** §2.1 scenario mapping.
- **Read work's evidence** from the cognitive-aid payload the `discover` phase **already pulls** (`flow-next-qa/workflow.md:71`; `flowctl spec export-cognitive-aid <spec-id>` carries per-task `evidence` as `{commits, tests, files_touched}`), or per-task `flowctl show <task-id> --json` (`{commits, tests, prs}`). **Do NOT** use `flowctl show <spec-id> --json | jq '.tasks[].evidence'` — spec-level task objects carry only `id/status/title/deps` (repo-scout `[VERIFIED]`).
- **CONSERVATIVE subtraction — by mapped-R-ID + deterministic-and-specific, not presence:** drop an AC from the live pass **only when** (a) the task's `satisfies` maps that AC's R-ID, AND (b) the work-evidence is a **deterministic, re-runnable command in `evidence.tests` directly tied to that R-ID / a non-live criterion**. A broad/ambiguous command (bare `pnpm test`) does NOT prove a specific AC ⇒ keep the live scenario. `files_touched`/`commits`/`prs` never prove an AC. **Always live-run** every runtime/UI/integration AC — narration (`evidence.tests` command strings, `delegation.verification_summary` self-report, `references/codex-delegation.md:390`) is never QA-grade captured evidence.
- **Preserve the hard rule** (`flow-next-qa/SKILL.md:16-18`): SHIP needs captured live evidence; no live app → BLOCKED, never SHIP-from-source. Unchanged.
- **Receipt-schema extension (additive — the pilot/make-pr contract):** extend the existing `qa_verdict` receipt writer (`flow-next-qa/workflow.md` §6.3) with lean additive fields: `head_sha` (= `git rev-parse HEAD` at QA time; the freshness key R1b/.2 reads), `branch`, `rid_coverage` (covered/total + per-R-ID outcome) and `open_p0p1` as **objects** (id + severity + reason + file), not bare ids — so make-pr can surface coverage + findings from the persisted receipt. Same file, no new artifact.
- **Committed-vs-transient receipts:** the only **committed** receipt stays `qa_verdict` (`.flow/review-receipts/qa-<spec-id>.json`). The existing BLOCKED note under `.flow/tmp/qa-<spec>/` is **transient/gitignored run-state** (fine; not a "new persisted artifact") — fold it into the normal `qa_verdict` BLOCKED write or keep it as transient notes; the no-new-artifact grep targets committed paths only.
- **Severity scoping:** P0/P1 → NEEDS_WORK; P2 informational.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-qa/SKILL.md:16-18` + mode-detection preamble — the hard rule + where autonomous parse must live
- `plugins/flow-next/skills/flow-next-qa/workflow.md:71,144-190,362-411` — discover, derive, qa_outcome matrix, **receipt writer §6.3 + §4.2 BLOCKED note**
- `plugins/flow-next/skills/flow-next-plan/SKILL.md` "Autonomous mode" — the `mode:autonomous` / `FLOW_AUTONOMOUS` parse shape to mirror
- `docs/flowctl.md:481` + `scripts/flowctl.py:14525,15775-15809` — the two evidence shapes
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md:390` — verification_summary is narration
**Optional:**
- `plugins/flow-next/skills/flow-next-qa/references/autonomy.md` — BLOCKED/NA degradation (don't fork)

## Acceptance
- [ ] Autonomous detection lives in SKILL.md mode-detection / the workflow preamble (before any prompt path); `mode:autonomous`/`FLOW_AUTONOMOUS=1` ⇒ no questions; undocumented target/accounts/missing-app ⇒ `BLOCKED` + clean exit, never a prompt.
- [ ] The `derive` phase reads work's recorded evidence (cognitive-aid payload / per-task `show`, NOT the non-working spec-level path) before producing the live scenario set.
- [ ] Subtraction is conservative: excluded only when the AC's R-ID is `satisfies`-mapped AND a deterministic, specific `evidence.tests` command covers it; broad/ambiguous tests and `files_touched`/`commits`/`prs` never subtract; runtime/UI/integration AC always live-run even if narrated.
- [ ] The hard SHIP-needs-live-evidence rule is preserved verbatim; narration never substitutes.
- [ ] `qa_verdict` receipt extended with `head_sha`, `branch`, `rid_coverage`, `open_p0p1` objects (additive); it remains the only **committed** persisted output; transient `.flow/tmp/` run-state is acceptable.
- [ ] QA receipt tests (e.g. `test_qa_receipt.py`) updated for the additive fields (`head_sha`, `branch`, `rid_coverage`, object-shaped `open_p0p1`) + the unchanged `qa_outcome`/`verdict` projection guard.
- [ ] NO new flowctl subcommand, NO persisted `.flow/qa/` committed artifact, NO new receipt file (grep confirms committed paths).
- [ ] Works for user-invoked `/flow-next:qa` too (shared executor, not pilot-only).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

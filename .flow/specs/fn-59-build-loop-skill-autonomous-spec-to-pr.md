## Conversation Evidence

> user: "runs the gamut of flow-next:plan into :work, into make-pr into resolve-pr"
> user: "it is similar to the ralph loop but a bit different as claude code/codex control the loop, not a shell script"
> user: "the new skill would ofc prompt in a way that we let the system know its running in an autonomous mode, no user questions etc"
> user: "i would not overineer it too much. for example if i prompt codex/claude right now to do plan, work and then make-pr, it is quite capable of doing those without human input, so this new orchestrator skill(s) should work fine too, right?"
> user: "we wouldn't reuse the ralph script right, only parts of the flowctl script?"
> user: "/goal and /loop are two different commands that exist in 2 different harnesses surely or no?"
> user: "if it should allow parallel execution of specs via worktrees"

## Goal & Context
<!-- Source: 55% [user] / 35% [paraphrase] / 10% [inferred] -->

A host-driven loop conductor. Instead of the human prompting plan → work → make-pr for each spec, this skill advances **one ready spec by one pipeline stage per invocation** and reports a structured verdict, so the host's `/loop` (Claude Code) or `/goal` (Claude Code + Codex) drives iteration until the backlog of ready specs is drained. Similar to Ralph's autonomous loop, but the agent host owns the loop — not an external shell script. Human judgment lives in the spec and the readiness gate (fn-58); the loop executes the mechanical pipeline.

## Architecture & Data Models
<!-- Source: 40% [user] / 50% [paraphrase] / 10% [inferred] -->

Single-tick conductor, driver-agnostic. Each tick:

- **SELECT** — first `open` + `ready` (fn-58) spec with all `depends_on_epics` satisfied, via `flowctl specs` (PR state is NOT probed at selection — it belongs to the all-done classification branch only); classify stage from spec + task JSON: `0 tasks → plan`; `planned & plan_review != ship → plan-review` (gate skipped when the review backend is `none` or `ASK`); `ready/in_progress tasks → work`; `all tasks done & completion_review != ship (backend configured) → work` (work's Phase-3g completion-review gate runs there and the caller sets `ship` — make-pr must never fire before it); `all tasks done & completion ship-or-ungated → probe PR state (the only gh touch): open PR → skip to next candidate; CLOSED-not-MERGED → NEEDS_HUMAN; none → make-pr`. The host judges stage — near-zero new flowctl.
- **ACT** — dispatch the one existing sub-skill with autonomous flags (`plan --depth/--research/--review`, `work --branch/--review`, `make-pr`). Never re-implements their logic.
- **VERIFY** — flowctl review-status fields (`plan_review_status` / `completion_review_status` at `ship`, where a review backend is configured) + confirmed task/spec status transitions before a tick counts as advanced — except `make-pr`, whose advancement evidence is a gh-confirmed new OPEN PR URL (it has no flowctl transition). Receipt files are Ralph-harness artifacts (written only under `REVIEW_RECEIPT_PATH`) and do not exist in a host-driven loop — verification rests on flowctl state.
- **REPORT** — a structured verdict consumable by a `/goal` validator or `/loop` cadence.

Autonomous signaling: sets a lightweight `FLOW_AUTONOMOUS=1` "no user questions" signal — **distinct from `FLOW_RALPH`** so it does *not* activate the ralph-guard hooks (built for the shell loop). plan, work, and make-pr gain `FLOW_AUTONOMOUS` awareness alongside their existing `FLOW_RALPH` checks; under it make-pr behaves as under Ralph (forced draft, hard-error instead of prompts) — the draft is flipped to ready by the ship-loop (fn-60) or a human. Reuses plan / work / make-pr + flowctl selection + review-status state; does **not** reuse `ralph.sh`.

### Resolved at planning (research + gap analysis, 2026-06-11)

- **Verdict contract (the /goal-critical piece):** the official `/goal` validator is transcript-blind — it reads the conversation only, never runs tools. So each tick ECHOES its verification evidence (flowctl status fields, task counts, PR url) into the output and ends with a single machine-greppable TERMINAL line: `PILOT_VERDICT=<ADVANCED|NO_WORK|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`. Nothing prints after it. Docs teach `/goal` conditions against this grammar (e.g. "stop when pilot prints PILOT_VERDICT=NO_WORK").
- **Autonomy mechanism:** `mode:autonomous` arg token primary (survives prose skill-invokes-skill; per-command env prefixes die with each tool call); `FLOW_AUTONOMOUS=1` env honored as secondary for process-level drivers. New parse branch in each sub-skill — do NOT overload capture's `mode:autofix`.
- **Tick arg surface:** bare `/flow-next:pilot` = one tick over the backlog; `--spec <id>` scope-lock; `--dry-run` = SELECT + classify report, no dispatch; passthrough: `--review=<backend>`, `--research=<grep|rp>`, `--depth=<...>` (defaults: grep, short, configured backend). Nothing else in v1.
- **Selection details:** two-pass (`specs --json` enumerate → `show <id> --json` per candidate — the listing is deliberately minimal); ID order via the stable id sort; dep "satisfied" = dep spec `status == done`; specs with `in_progress` tasks assigned to ANOTHER actor are skipped (collision avoidance); pilot hard-errors if invoked under `FLOW_RALPH` (Ralph and pilot are alternative drivers, never nested). Stage set is exactly {plan, plan-review, work, make-pr} — capture/interview/qa are never dispatched. The completion-review gate is reached THROUGH work (Phase 3g), never as a pilot stage. **Status-setter convention differs per review skill and is load-bearing:** plan-review sets `plan_review_status` itself (its workflow Phase 4); completion-review does NOT — the caller (work 3g) sets it. **gh probe failure semantics:** the open-PR probe runs only when classification reaches the all-done branch; `gh` missing/unauthenticated/API-failure there → `NEEDS_HUMAN` (a PR can't be created without gh anyway); earlier stages never touch gh.
- **Branch resolution across ticks (explicit matrix):** pilot owns it. Branch exists + stage work → checkout `branch_name`, dispatch `work <spec> --branch=current mode:autonomous`; branch absent + first work tick → dispatch `--branch=new`; stage make-pr → require + checkout the existing `branch_name` (absent branch at make-pr = inconsistent state → NEEDS_HUMAN). make-pr then auto-detects the spec from the branch as it already does.
- **make-pr advancement carveout:** make-pr produces NO flowctl state transition — its advancement evidence is external: before = no OPEN PR for the branch, after = a gh-confirmed OPEN PR URL. Pilot echoes that URL as the evidence and counts the tick ADVANCED on it; never judge make-pr by flowctl fields (a successful PR tick must not record a strike).
- **Failure semantics:** healthy-but-no-advance (sub-skill returned cleanly, the stage's advancement evidence unchanged — flowctl fields for plan/plan-review/work, the PR probe for make-pr) → strike recorded, verdict `BLOCKED` with `strike=1/2` (spec stays ready; next tick retries) or `strike=2/2` (spec unready'd, reason persisted). Sub-skill crash / dirty tree left behind / dirty tree at tick start → `NEEDS_HUMAN`, state left untouched for diagnosis (no auto-reset of claims). Review gate skipped when backend is `none` OR `ASK` (review-backend returns ASK when unconfigured).
- **Strikes ledger:** `$(git rev-parse --git-common-dir)/flow-next/pilot-strikes.json` — under `.git`, so it is shared across worktrees AND can never be swept into a commit by work's mandatory `git add -A` (a `.flow/` path would be per-worktree and committable — rejected). Skill-owned scratch, no flowctl plumbing. Schema: `{<spec-id>: {count, stage, reason, ts}}`. Cleared on ADVANCED for that spec. A human re-blessing an unready'd spec (`spec ready`) overrides: at SELECT, a ready spec with a count≥2 entry gets its entry cleared (re-bless = explicit human reset).
- **Unattended-rp caveat:** the rp review backend needs the GUI app; an overnight unattended run can hang on it. v1 documents rp as an attended-driver caveat (use codex/copilot or `--review=none` for unattended runs); no timeout machinery in the tick — wall-clock/iteration caps belong to the DRIVER (`/goal --tokens`, condition clauses), never the tick.
- **Codex driver caveats (docs):** Codex goals are opt-in (`[features] goals = true`, CLI ≥0.128.0); there is NO documented $skill-in-goal syntax on Codex — the docs page teaches a plain-text objective that names the pilot behavior + verdict grammar. Claude needs v2.1.139+ (/goal) / v2.1.72+ (/loop).
- **Sequencing bookkeeping:** fn-60 gains `depends_on_epics += fn-59` (done at plan time); fn-54's prompt-optimization passes over plan/work/make-pr must baseline AFTER fn-59's autonomy patches land.

## API Contracts
<!-- scope: technical -->

- **Invocation** `/flow-next:pilot` — v1 arg surface: bare (one tick), `--spec <id>`, `--dry-run`, and the passthroughs `--review` / `--research` / `--depth`. Branch is pilot-owned via the resolution matrix, never user-specified. [user]/[inferred]
- **Output** — structured verdict `ADVANCED | NO_WORK | BLOCKED | NEEDS_HUMAN` + spec / PR references, printed for the host loop to act on. [paraphrase]
- **Env** — sets `FLOW_AUTONOMOUS=1` when dispatching sub-skills. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- Don't-thrash guard: a spec that fails to advance twice → clear its `ready` flag via `flowctl spec unready` (fn-58 plumbing — selection then skips it; `flowctl block` is task-level and cannot block a spec) and report `BLOCKED` with the reason. The verdict must carry the reason, since an un-readied-by-failure spec looks identical to a never-blessed one in listings. [paraphrase]
- Review backend `none`: the plan-review / impl-review gates are skipped and "advanced" rests on task/spec status transitions alone — the gate must never deadlock selection. [inferred]
- A PR closed without merging (a human rejected it) → report `NEEDS_HUMAN`; never silently re-open a PR for that spec. [inferred]
- Iteration / budget ceilings are the host loop's concern, but the skill must report `NO_WORK` cleanly so the host can stop. [inferred]
- If a sub-skill would still ask under autonomy (genuinely ambiguous), report `NEEDS_HUMAN` rather than block on a question. [paraphrase]
- Cross-platform: canonical Claude tool names; `sync-codex.sh` rewrites `AskUserQuestion` → numbered prompt and `Task` → `spawn_agent`. [strategy:Cross-platform parity]
- Sub-skills now ship fn-57's end-of-run tracker self-check (four-state `Tracker sync:` summary slot + one-cycle retro-fire, 1.11.0) — a pilot tick inherits tracker observability for free; the verdict passes the slot state through rather than re-checking. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A new skill `/flow-next:pilot` advances exactly one ready spec by one pipeline stage per invocation and exits with a structured verdict. [paraphrase]
- **R2:** Stage selection picks the first `open` + ready (per fn-58) spec whose `depends_on_epics` are all satisfied and that carries no other-actor task claims, and classifies its stage (plan / plan-review / work / make-pr) from flowctl spec + task state — PR state is probed only in the all-done classification branch, never at selection. [paraphrase]
- **R3:** It dispatches the existing stage skills (plan, plan-review, work, make-pr) with autonomous flags, never re-implementing their logic. [user]
- **R4:** It runs under autonomous mode — signalled to sub-skills primarily via a `mode:autonomous` arg token (env vars do not survive across tool calls; capture's `mode:autofix` parse is the precedent), with `FLOW_AUTONOMOUS=1` env honored when present (Ralph-style process-level export). Sub-skills ask no user questions and pick safe defaults; neither signal activates ralph-guard hooks. [user]/[inferred]
- **R5:** A tick counts as advanced only after flowctl review-status fields reach `ship` (where a review backend is configured; gates are skipped under backend `none`/`ASK`) plus a confirmed task/spec status transition — except the make-pr stage, whose advancement evidence is a gh-confirmed new OPEN PR URL. [paraphrase]
- **R6:** Verdicts are `ADVANCED | NO_WORK | BLOCKED | NEEDS_HUMAN`, shaped so a `/goal` validator or `/loop` cadence can decide whether to continue. [paraphrase]
- **R7:** A spec that fails to advance twice is taken out of selection — its `ready` flag is cleared and the reason is reported in the `BLOCKED` verdict — and skipped on later ticks; no thrashing. [paraphrase]
- **R8:** It is driver-agnostic — works invoked by Claude Code `/loop`, Claude Code `/goal`, or Codex `/goal`. [user]
- **R9:** Cross-platform parity — canonical Claude tool names; `sync-codex.sh` handles the Codex mirror rewrites. [strategy:Cross-platform parity]
- **R10:** Docs + flow-next.dev updated — new skill page, both navbars, changelog, command reference, version bump. The hero pillar grid is data-array-extensible since fn-57.8 — evaluate adding a loop/autonomy pillar as part of the site work ("may need to add more there later too, like the loop stuff"). [user]
- **R11:** plan, work, and make-pr parse the `mode:autonomous` token AND detect `FLOW_AUTONOMOUS` env alongside `FLOW_RALPH` — in their question-suppression branches ONLY (never ralph-guard/receipt paths); under autonomy work defaults deterministically to `--branch=new`, and make-pr forces draft + hard-errors instead of prompting. [inferred]

## Boundaries
<!-- scope: business -->

- Build-loop **stops at make-pr**. PR-feedback resolution, merge, and release are the ship-loop's job (spec 3). [user]
- Planning is **inside** the loop (the agent plans the implementation); the human gate is spec readiness (fn-58), not a plan-review sign-off. [user]
- Parallel execution of multiple specs via worktrees is **out of scope for v1** (serial, one spec per tick); a flagged worktree-parallel mode is a later enhancement. [user]
- Does **not** reuse `ralph.sh` or its hooks — only flowctl selection + review-status state. [user]
- No new selection engine in flowctl beyond what exists; the host judges stage. [paraphrase]

## Decision Context
<!-- scope: both -->

Host-driven (in-session) loop vs Ralph's external shell loop: the agent host (`/loop`, `/goal`) owns iteration, so the skill is a single tick + verdict, not a runner — the "orchestration loop" layer above the harness, distinct from the shell-driven ralph loop. It leans on existing capability: prompting an agent to do plan → work → make-pr already works hands-off with the right flags, so the skill's value is **selection + autonomous defaults + the verdict contract + the don't-thrash guard**, not new mechanics. A lighter `FLOW_AUTONOMOUS` signal (vs reusing `FLOW_RALPH`) avoids dragging in ralph-guard's shell-loop receipt choreography. Depends on fn-58 for its selection gate. [strategy:Ralph autonomous mode]

## Strategy Alignment
<!-- STRATEGY.md populated 2026-05-16 -->

- Extends the **Ralph autonomous mode** track to a host-driven loop with the same receipt-gated, quality-first discipline. [strategy:Ralph autonomous mode]
- **Cross-platform parity** track — driver-agnostic + sync-codex mirror. [strategy:Cross-platform parity]
- *"host agent IS the intelligence"* — no new flowctl selection engine; the host judges stage. [strategy]

## Quick commands

```bash
# Dry-run a tick (selection + classification only)
# /flow-next:pilot --dry-run         (skill invocation — no flowctl additions)

# Verdict grammar smoke (after .1): drive condition example
# /goal keep running /flow-next:pilot until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns

# Autonomous sub-skill smoke (after .2)
# /flow-next:make-pr <spec> mode:autonomous   -> forced draft, zero questions
```

## Early proof point

Task fn-59.1 validates the conductor model (transcript-evidence + terminal verdict + two-pass selection + strikes ledger). If the /goal validator can't reliably read the verdict grammar in practice, re-evaluate the REPORT contract before patching the sub-skills.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Single-tick skill + structured verdict | fn-59.1 | — |
| R2 | Selection predicate + stage classification | fn-59.1 | — |
| R3 | Dispatches existing skills, never re-implements | fn-59.1 | — |
| R4 | Autonomous mode (token + env), no ralph-guard activation | fn-59.1, fn-59.2 | — |
| R5 | Advance = review-status fields + status transitions | fn-59.1 | — |
| R6 | Verdict enum shaped for /goal//loop | fn-59.1 | — |
| R7 | Don't-thrash: two strikes → unready + reasoned BLOCKED | fn-59.1 | — |
| R8 | Driver-agnostic (Claude /loop, /goal; Codex /goal) | fn-59.1 (contract), fn-59.3 (drive docs) | — |
| R9 | Cross-platform parity / sync-codex mirror | fn-59.1 (registration), fn-59.3 (regen+audit) | — |
| R10 | Docs + site + hero pillar + version | fn-59.3 | — |
| R11 | plan/work/make-pr autonomous-mode parsing | fn-59.2 | — |

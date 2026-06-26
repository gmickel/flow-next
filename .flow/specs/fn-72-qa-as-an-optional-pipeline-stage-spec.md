# fn-72 QA as an optional pipeline stage — lean, agentic, evidence-aware

## Goal & Context
<!-- scope: business -->

`/flow-next:qa` exists today as a **user-invoked, off-to-the-side** skill (via the `qa` command wrapper): a human runs it when they remember to. It already does the hard part — derive scenarios from the spec (AC → scenarios, R-IDs → coverage, boundaries → exclusions), drive the live app via flow-next-drive, file P0/P1/P2 findings, and emit a `qa_outcome` (`SHIP` / `NEEDS_WORK` / `NA` / `BLOCKED`). But it lives outside the build loop, so the autonomous span (`plan → plan-review → work → make-pr`) ships a draft PR with only *static* review.

This makes QA an **optional, config-gated (default off), autonomy-safe pilot stage** that runs **one final live pass over the complete build at all-tasks-done**, before make-pr. The intent is small and concrete: **the app already runs on the dev's machine during `work` — so run an initial QA against it.** This **augments, it does not replace,** staging/CI QA or manual QA; it is the cheap first live pass that catches the obvious runtime breakage before a human ever opens the PR.

Two design commitments shape it: **(1) lean + agentic** — the host derives and drives in-context (the same agentic app-driving the worker already does while building UI), with **no persisted artifacts, no new flowctl plumbing, and no extra receipts** beyond the one `qa_verdict` that rides the PR/land hand-off (a receipt matters only when handing off to another system or human). **(2) evidence-aware** — it leans on what `work` already verified and only runs what work didn't (and structurally can't) cover.

## Architecture & Data Models
<!-- scope: technical -->

- **A config-gated pilot stage reusing the existing `/flow-next:qa` skill — net-new is the pilot wiring only.** No new skill, **no new flowctl subcommand, no persisted `.flow/qa/` test-case file**. The host derives scenarios in-context (the QA skill's `derive` phase) and drives the **local running app** agentically; R-ID coverage is reported in the verdict / PR body, not a tracked artifact. Net-new flowctl is **zero new subcommands/engines — one `pipeline.qa` config-key default only**; pure host-agent skill wiring.
- **Reverses pilot's "QA is never a stage" — and the reversal is principled.** pilot's `SKILL.md` forbids `{capture, interview, QA, resolve-pr, merge, release}` as stages, but for **three different reasons**: capture/interview are **human authoring upstream of the consent boundary**; resolve-pr/merge/release are **land's territory downstream of the PR** (merge is the human gate); **QA alone was excluded for a *capability* reason** — it needed a live app pilot couldn't guarantee and had no autonomy-safe "can't verify" behavior. fn-72 supplies exactly those missing capabilities (opt-in gate + autonomy-safe verdict), so QA — a pre-ship *verification* gate on the same artifact pilot builds, the live-app sibling of the impl-review gate that **already runs inside `work`** — can join the stage set. **The other five stay forbidden, for their distinct (loop-ownership / consent) reasons** — opening QA is not a precedent to open them.
- **Pipeline placement:** `plan → plan-review → work → **qa** → make-pr`, with QA at the **all-tasks-done** juncture (one live pass per spec over the complete build), not per-tick. The net-new pilot edits are the Forbidden-list line (QA removed *only under the gate*), the classify table, branch matrix, dispatch list, and the `PILOT_VERDICT` stage entry.
- **Evidence-aware — lean on what `work` already verified.** Before driving, read work's recorded evidence — via the **cognitive-aid payload the QA `discover` phase already pulls** (`flowctl spec export-cognitive-aid <spec-id>`, which carries per-task `evidence`), or per-task `flowctl show <task-id> --json`. *(NOT `flowctl show <spec-id> --json | jq '.tasks[].evidence'` — the spec-level task objects carry only `id/status/title/deps`, no `evidence`.)* **Subtract only the AC whose work-evidence is a deterministic, re-runnable check** (a real test/lint/build command in `evidence.tests` / a Quick command) — never re-run those. **Always keep + live-run every AC whose satisfaction is runtime/UI/integration behavior**, even if work narrated it done: work's `evidence.tests` are command strings work *says* it ran and `delegation.verification_summary` is the worker's *self-report* (the work skill itself says don't trust it as the sole gate) — that is narration, and QA's hard rule (SHIP needs captured live evidence) cannot honor narration. The subtraction keys on evidence **type, not presence**.
- **Verdict is surfaced, not a hard loop-block (gate reads `qa_outcome`, never the `verdict` projection).** The receipt emits `qa_outcome ∈ {SHIP, NEEDS_WORK, NA, BLOCKED}` and *separately* projects a Ralph-guard `verdict` where **`BLOCKED→NEEDS_WORK`** — the gate MUST read `qa_outcome`. Routing: `SHIP` / `NA` / `BLOCKED` → advance to make-pr cleanly; **`NEEDS_WORK` → still advance to make-pr (draft) and surface the findings** into the PR body + bug-memory track + (when the bridge is active) a tracker-sync comment. QA never blocks the build loop — it's an advisory live-test signal the **human reviewer + the land gate** act on (merge stays human). *(Interactive mode MAY route NEEDS_WORK back to `work`, bounded to avoid work↔qa thrash; autonomous surfaces + proceeds.)*
- **Local-dev-app scope.** QA drives the instance already up on the dev's machine (work brought it up); when no local app is reachable it returns **BLOCKED → advance** — it's the optional augmenting pass, not the CI/staging gate.
- **Reuses:** the QA skill (executor + its hard rule), flow-next-drive (the agentic driver ladder; the fn-71 CUA rung is *optional* reach once it ships — agent-browser is the only assumed driver), the existing `qa_verdict` receipt, the bug-memory track, and pilot's stage machine. No new persistence.

## API Contracts
<!-- scope: technical -->

- **Config:** `pipeline.qa ∈ {off (default), on}` — global config only. On ⇒ pilot inserts the `qa` stage at all-tasks-done. Default **off**. *(A per-spec override is an explicit out-of-scope follow-on — fn-72 ships the global key only.)*
- **No new flowctl, no new artifact.** The QA stage is host-agent skill work; the only persisted output is the existing `qa_verdict` receipt at `.flow/review-receipts/qa-<id>.json`, which rides the PR/land hand-off.
- **Gate** reads `qa_outcome` from that receipt (NOT the Ralph-guard `verdict` projection where `BLOCKED→NEEDS_WORK`).
- **Pilot verdict:** the `qa` stage emits `ADVANCED <id> qa`; `NEEDS_WORK` still advances (findings surfaced on the draft PR), so the build loop never stalls.
- **Cross-platform:** canonical Claude names; `sync-codex.sh` regenerates; `/goal` driver parity.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Augments, never replaces** CI/CD-time QA, staging QA, or manual QA — it is the initial local-dev live pass only.
- **BLOCKED (no local app reachable) → advance** — optional augmenting stage, never wedges a pipeline that can't run it. `NA` (no driveable UI — the common backend/CLI case) → advance.
- **SHIP needs captured live evidence** — the hard rule is intact in the pilot context; work's narration (tests list / `verification_summary`) never counts as SHIP.
- **Evidence-aware subtract keys on evidence *type*** (deterministic re-runnable check) not presence; runtime/UI AC always gets a live pass.
- **Lean — no per-tick spin** (once at all-done), **no persisted artifacts, no extra receipts** beyond the hand-off `qa_verdict`.
- **Don't-thrash:** `NEEDS_WORK` surfaces-and-proceeds by default (no loop); the optional interactive back-to-work path is bounded (reuse pilot's strike/auto-block reflexes).
- **Autonomy-safe:** never prompts; in autonomous/backlog mode SHIP/NA/BLOCKED advance, NEEDS_WORK surfaces + advances.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A config gate (`pipeline.qa`, default **off**) inserts a `qa` stage at the **all-tasks-done** juncture (before make-pr); with it off, the pipeline is byte-for-byte unchanged.
- **R1b (idempotence — pilot is single-tick):** the `qa` classification is **gated on the absence of a *fresh* `qa_verdict` receipt** for the spec. **Freshness is defined by a `head_sha` field added to the existing `qa_verdict` receipt** (additive, not a new artifact): a receipt is fresh iff `receipt.id == <spec-id>` (the existing receipt's spec-id field, `workflow.md:423`) AND `receipt.head_sha == git rev-parse HEAD` AND `qa_outcome` is a valid terminal value. All-done + `pipeline.qa==on` + no fresh receipt ⇒ classify `qa`; a fresh receipt ⇒ fall through to the make-pr probe. Without this, a single-tick pilot re-classifies `qa` forever and never reaches make-pr.
- **R2:** **Lean + agentic — no new flowctl subcommand/engine and no persisted test-case artifact.** The host derives scenarios in-context and drives the local running app agentically (reusing the `/flow-next:qa` executor); R-ID coverage is reported in the verdict/PR, not a tracked file. *(The one legitimate mechanical flowctl touch is registering the `pipeline.qa` config-key default `"off"` in `get_default_config()` — the same trivial schema plumbing every config key gets, e.g. `artifacts.html.enabled`; NOT a new command, extractor, or engine.)*
- **R3:** Reverses pilot's "QA is never a stage" **only under the gate** — QA removed from the Forbidden list / added to the classify table, branch matrix, dispatch list, and `PILOT_VERDICT` stage entry *when gated on*; **capture/interview/resolve-pr/merge/release remain forbidden** (distinct loop-ownership / consent reasons).
- **R4:** **Evidence-aware** — reads work's recorded evidence first; subtracts from the live pass only AC proven by a deterministic re-runnable check (a command in `evidence.tests` / a Quick command); **always live-runs every runtime/UI/integration AC even if work narrated it done.**
- **R5:** **SHIP needs captured live evidence** — preserved unchanged in the pilot context; work narration (incl. `verification_summary`) never substitutes for it.
- **R6:** **Augmenting, local-dev scope** — drives the app already up on the dev machine; `BLOCKED` (no local app) and `NA` (no UI) advance; never positioned or documented as a replacement for CI/staging/manual QA.
- **R7:** **Verdict surfaced, not loop-blocked** — the gate routes on `qa_outcome` (not the `verdict` projection); `SHIP/NA/BLOCKED` advance; **`NEEDS_WORK` still advances to the draft PR and surfaces findings** (PR body + bug memory + tracker comment when active). Never blocks the build loop; the human review + land gate act on it. (Interactive may route back to work, bounded.)
- **R8:** **Receipts only at the hand-off** — the existing `qa_verdict` receipt rides the PR/land hand-off; **no new receipts or artifacts** are introduced (a receipt matters when handing off to another system/human, not for the in-loop pass).
- **R9:** Autonomy-safe (no prompts); cross-platform parity (canonical names, sync-codex regen, `/goal`); plugin version bumped. **Full documentation sweep — this changes the pipeline, so every surface that describes the pipeline or QA must update** (per CLAUDE.md doc-update discipline):
  - **Repo:** the qa SKILL, `docs/ralph.md` + the pilot/pipeline docs (add the optional `qa` stage to `plan → … → make-pr`), `docs/README.md` index.
  - **flow-next.dev:** the qa page (sharpen the framing — QA **augments, never replaces** staging/CI/manual QA; like everything in flow-next it reduces human work agentically and **surfaces problems to humans**), the pilot/pipeline page (the new optional stage), BOTH navbars, the changelog, `FLOW_NEXT_VERSION`.
  - **Downstream narrative docs (consider + update):** the **AI×SDLC guide** — `guides/flow-next.md` "## The pipeline: idea to merged PR" (the optional QA stage in the idea→merged-PR breakdown) + the QA sections (`phased-rollout.md` "### 3. Testing & Quality Assurance", `ai-readiness.md` "### The dogfood skill: automated QA", `production-grade.md` test/eval sections, `metrics.md` "### Test coverage delta") — applying the same "augments not replaces, surfaces to humans" framing; and the **GF microsite** (`code-factory-package`) where the pipeline/QA is described.

## Boundaries
<!-- scope: business -->

- **Augmenting initial QA on the local dev app — NOT a replacement** for CI/CD-time QA, staging QA, or manual QA.
- **Lean + agentic — no new flowctl subcommand/engine, no persisted test-case artifacts, no extra receipts** (the host derives + drives in-context; receipts only at the human/land hand-off). The lone mechanical flowctl touch is the `pipeline.qa` config-key default in `get_default_config()` (schema plumbing, not a command).
- **Optional, default off** — environments without a local app are never blocked (BLOCKED/NA advance).
- **Reuses the QA skill** — no fork, no second QA engine; net-new is pilot stage wiring + the evidence-aware dedup.
- **Not a merge gate** — surfaces its verdict into the draft PR; `land` + human review stay the merge authority.
- **The other five forbidden pilot items stay forbidden** — opening QA is not a precedent to open land's stages or the authoring stages.
- **Drivers are fn-71's concern** — consumes flow-next-drive; **functionally fn-72 needs only agent-browser** (the always-present driver). fn-71's CUA rung widens reach but is **not a functional prerequisite**. The `depends_on_epics: fn-71` edge in the sidecar is a deliberate **build-order/sequencing** choice (Gordon's `71 → 72 → 68` ordering), not a functional gate — recorded so the prose and the sidecar agree.
- **Self-improvement / flaky-case management** is a follow-on, not this spec.

## Decision Context
<!-- scope: both -->

### Motivation
The cheapest high-value verification — does the running product actually work — lives outside the loop today. The app is already up on the dev's machine during `work`; running an initial agentic live pass over the complete build, before a human opens the PR, catches obvious runtime breakage early. It augments (never replaces) the real QA that still happens at staging/CI and by hand.

### Implementation Tradeoffs
- **Lean + agentic over artifacts/receipts (the load-bearing steer):** an earlier draft added a persisted `.flow/qa/<spec-id>/cases.json` + a `flowctl qa cases` subcommand + receipt emphasis. **Rejected** — the host agent IS the intelligence; it derives and drives in-context and surfaces findings. Receipts matter only at a hand-off to another system/human (the `qa_verdict` on the PR/land hand-off) — not for the in-loop pass. This drops fn-72's net-new flowctl to **a single config-key default** (`pipeline.qa: off` in the schema) — **no new subcommand, engine, extractor, or artifact**. The `qa_verdict` receipt gains lean additive fields (`head_sha`, `rid_coverage`, `open_p0p1` objects) but stays the only persisted output.
- **QA-as-optional-pilot-stage is justified because the exclusion was capability-contingent**, not loop-ownership (resolve-pr/merge/release) or consent (capture/interview). fn-72 supplies the missing capabilities; the other five stay forbidden.
- **Evidence-aware, keyed on evidence type:** work already verifies (tests + the worker drives the app agentically while building); don't re-run deterministic checks, but always live-run runtime/UI AC because work's evidence there is narration, not QA-grade captured evidence.
- **Surface, don't block (D3):** `NEEDS_WORK` makes the draft PR + surfaces findings rather than holding the loop — consistent with "draft PR is the terminus, the human gate decides." Merge stays human. Grounded in DORA's research: heavyweight blocking approval gates correlate with *worse* delivery/stability, advisory feedback that *informs* the path to production correlates with better outcomes ([DORA — Streamlining change approval](https://dora.dev/capabilities/streamlining-change-approval/)); and automated QA as fast-feedback that *complements* human judgment, not replaces it ([DORA — Test automation](https://dora.dev/capabilities/test-automation/)).
- **Placement at all-done (D2):** QA needs a complete build; one pass per spec at the all-done juncture, not per-tick.
- **Default off:** QA needs a local app; forcing it on would break the zero-friction default. Once on, it runs automatically every all-done (no per-run remembering).

## Strategy Alignment
- **"Host agent IS the intelligence; flowctl thin helpers"** — fn-72 adds **no new flowctl subcommand/engine and no new artifact** (only a `pipeline.qa` config-key default + additive `qa_verdict` receipt fields); it is pure host-agent skill wiring + agentic driving. The leanest possible expression of the architecture rule.
- **Ralph autonomous mode track** — adds a live-verification station to the pilot/land assembly line; evidence over narration by construction; surface-don't-block matches the loop discipline.
- **Self-improving through normal work** — QA findings feed the bug-memory track as a side-effect of running the stage.
- **Cross-platform parity** — canonical names + sync-codex; reach widens once fn-71 (CUA rung) ships (optional).
- Tightens **idea-to-merge quality** — a live-tested draft PR, not just a built one.

## Early proof point

Task `fn-72-qa-as-an-optional-pipeline-stage-spec.1` (the evidence-aware QA pass in the shared `flow-next-qa` skill) proves the core lean+agentic thesis — the host reads work's evidence + derives + drives in-context with **zero new flowctl/persistence**, and it's usable by user-invoked QA immediately (not pilot-gated). If `.1` cannot do the evidence-aware subtraction without a persisted artifact / new flowctl, reconsider the "lean, no-plumbing" stance before wiring the pilot stage in `.2`.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Config gate `pipeline.qa` (default off) inserts qa at all-done | .2 | — |
| R1b | Idempotent — qa classified only when no fresh `qa_verdict` receipt | .1 (adds `head_sha`), .2 (freshness/verify) | — |
| R2 | Lean+agentic — no new flowctl subcommand/engine (one config default only), no new artifact; host derives+drives | .1 (derive), .2 (wiring) | — |
| R3 | Reverses "QA never a stage" only under the gate; other five stay | .2 | — |
| R4 | Evidence-aware — subtract deterministic checks, runtime always live | .1 | — |
| R5 | SHIP needs captured live evidence (hard rule preserved) | .1 | — |
| R6 | Augmenting local-dev; BLOCKED/NA advance | .2 (routing), .1 (BLOCKED outcome) | — |
| R7 | Verdict surfaced not loop-blocked; routes on `qa_outcome` | .2 | — |
| R8 | Receipts only at the hand-off (no new receipt/artifact) | .1, .2 | — |
| R9 | Autonomy-safe + full doc sweep (4 repos) + version | .3 | — |

## Conversation Evidence
> user: "separately we should consider whether QA should become a fixed (pot optional) part of the pipeline with the test cases being extracted from the spec and context and tested etc, probably a sep spec"
> user: "why does pilot forbid QA … what is the difference between the impl-review loop and QA? We can always raise things to the human at any point via the tracker-sync and the spec and the PR"
> user: "the work skill already does some QA generally, especially if noted in the acceptance criteria of the spec, this is usually written in the spec notes as evidence. Would probably make sense to not run this again during the QA stage?"
> user (the lean steer): "as agentic as possible, the work skill already fires up something like agent browser and then iterates if it finds problems … we dont need more receipts etc. lean on agentic. receipts are important if handing off to another system. … IF the app that is being developed works on the local dev's machine, why not run an initial QA? we are not talking about replacing QA at CI/CD time or manual QA, just augmenting it."
> user (D2): placement "Once at all-tasks-done, before make-pr"; (D3): "Make the draft PR + surface findings"

Reference: `/flow-next:qa` (fn-53, done) — derive + the hard SHIP-needs-live-evidence rule; flow-next-drive (fn-51) + the optional fn-71 CUA rung; pilot pipeline (fn-59 / fn-68); `work` evidence schema (`.flow/state/tasks/<id>.state.json` `evidence`, task `## Evidence`). Design grounded by the `qa-pilot-design-investigation` workflow (2026-06).

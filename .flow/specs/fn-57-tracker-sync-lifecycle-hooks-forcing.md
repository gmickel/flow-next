## Conversation Evidence

> user: "you didn't link the pr properly, tracker sync didn't work somehow"
> user: "why did it not happen before, i had similar issues in codex in another project"
> user (relaying a Codex session in another project, GNO-3): "you also didn't do it on the work steps, you also didn't link the pr etc etc, help me understand if my prompting in the skills was wrong or was this a one-off thing"
> [Codex agent's diagnosis, shared by user]: "Not your prompting. Mostly my execution miss. ... these hooks are prose/checklist obligations, not executable gates. The skill says 'invoke tracker-sync' but the actual snippet body is `:`. That makes it agent-discipline-dependent. ... The durable fix is to make flow-next-work / flow-next-make-pr call a real flowctl sync lifecycle ... or equivalent wrapper, so missing tracker sync is observable and receipts are required before final."
> user: "do we have issues with our tracker-sync stuff"
> user: "yes capture it"
> user: "this is not just for linear right, but for all trackers?"

> [agent investigation this session, confirming the diagnosis against the code]: make-pr §4.6a (the PR↔issue `Ref <identifier>` line) IS deterministic bash that appends to the body before `gh pr create` (workflow.md:1341-1343) — the miss there was execution-fidelity (the agent hand-rolled `gh pr create` and skipped it). The lifecycle hooks — `work.firstClaim → In Progress` (phases.md:210), `work.done → comment` (:282), make-pr §5.6 enhancement — are executable GATES wrapping a `:` no-op whose only body is a prose comment ("invoke the flow-next-tracker-sync skill"). On the MCP rung (no `LINEAR_API_KEY`), flowctl has no MCP access, so the action is inherently agent-driven and can't be a pure flowctl call.

## Goal & Context
<!-- scope: business -->

<!-- Source-tag breakdown: 55% [user] / 25% [paraphrase] / 20% [inferred] -->

flow-next's tracker-sync bridge (fn-52, shipped) wires lifecycle touchpoints — claim a task → move the issue In-Progress, finish a task → post a comment, open a PR → link it to the issue. In real use these touchpoints **silently don't fire**: a PR opened without its issue link, work steps that never moved the tracker. [user] It has happened on more than one host — both a Claude session and a Codex session in a separate project (GNO-3) hit it [user] — so it is **not a prompting problem and not model-specific** [paraphrase]. Root cause: the lifecycle hooks are **prose/checklist obligations, not executable gates** — the skill says "invoke the tracker-sync skill" but the actual snippet body is a `:` no-op, making them agent-discipline-dependent, and nothing fails when they are skipped. [paraphrase] When an agent is driving the loud gates (tests, review, PR-create — which fail visibly), the quiet tracker side-effects get dropped. [inferred] This spec makes the tracker lifecycle **observable and forcing** so a configured-but-didn't-fire touchpoint is a detectable gap, not a silent one. [paraphrase]/[inferred]

This is **tracker-agnostic — for ALL trackers, not just Linear**: Linear and GitHub today (and any future adapter), via the bridge's transport-blind adapter interface. [user] The Linear symptoms surfaced it, but the weakness is in the shared lifecycle-hook layer that every adapter routes through. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

The split is the existing flow-next architecture rule (mechanical → deterministic/flowctl + receipts; judgment → skill), applied to the tracker hooks: [inferred]

The forcing layer lives in the **transport-blind adapter interface** every tracker routes through, so it applies uniformly to Linear, GitHub, and future adapters. The deterministic-vs-receipt choice is **per-transport-capability, not per-tracker**: [inferred]/[user]

- **Mechanical ops** that need no judgment run **deterministically wherever the active transport gives flowctl/CLI direct access** — GitHub via `gh` (always); Linear via GraphQL (when `LINEAR_API_KEY` is set); the make-pr §4.6a reference line, already tracker-aware (`Ref WOR-N` for Linear, `Refs #N` for GitHub). [inferred]
- **Agent-only transports** — where the active transport is reachable **only by the host agent** (e.g. Linear's MCP rung, which flowctl can't call) — can't be made deterministic. There the forcing function is the **receipt** (below), not determinism. Same shape for any future agent-only adapter. [inferred]
- **Judgment ops** — the agentic 3-way body reconcile/merge — **stay a skill** for every tracker; this spec does NOT make those deterministic. [inferred]
- **Per-event sync receipt** (tracker-neutral) — each configured lifecycle touchpoint emits a receipt recording `fired` | `skipped:<reason>` | `errored`, in the existing proof-of-work receipt model Ralph already uses to gate state transitions. [paraphrase]/[inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- **Bridge inactive / event opted-out** is a legitimate `skipped` (no-op), not a failure — must read as a clean receipt, never an error. [inferred]
- **Execution-fidelity gap (make-pr §4.6a):** the ref-append is already deterministic but an agent that hand-rolls `gh pr create` bypasses it — the forcing function must catch "PR opened but no issue link" even when the skill's own bash wasn't run literally. [inferred]
- **Best-effort, never blocking the primary work:** a tracker failure must stay non-fatal (the PR is already open; the task is already done) — observability must not turn a tracker hiccup into a hard stop. [inferred]
- **Ralph-safe:** receipts + any queue behavior must preserve the autonomous-loop invariants. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Every configured lifecycle touchpoint (`work.firstClaim`, `work.done`, make-pr PR-link, and the others in the `perEvent` set) emits a **per-event sync receipt** — `fired` / `skipped:<reason>` / `errored` — so a configured-but-didn't-fire touchpoint is **observable**, not silent. [paraphrase]
- **R2:** The receipts are **surfaced + checkable before a run is considered final** (end-of-`work` summary and post-make-pr), so a missing tracker side-effect is caught rather than discovered later by the user. [paraphrase]
- **R3:** Mechanical tracker ops that need no judgment run **deterministically** wherever the active **adapter/transport** allows direct flowctl/CLI access — the make-pr §4.6a reference line (`Ref WOR-N` / `Refs #N`), and status/comment on the GitHub-`gh` and Linear-GraphQL transports — rather than as a `:`-no-op prose obligation. [paraphrase]/[inferred]
- **R4:** The make-pr **PR↔issue link reliably fires on a real `/flow-next:make-pr` run for whichever tracker is active** — the execution-fidelity gap (agent hand-rolls `gh pr create` and skips the deterministic ref-append) is closed by the forcing function. [user]/[inferred]
- **R5:** On any **agent-only transport** (e.g. Linear's MCP rung — flowctl can't call it) where the op is inherently agent-driven, the forcing function is the **receipt gate** (the agent must record `fired`/`skipped`), since the op cannot be a pure flowctl call. [inferred]
- **R6:** The **agentic 3-way body merge stays a skill** — for every tracker — this spec hardens only the mechanical status / comment / link touchpoints, not the judgment-bearing reconcile. [inferred]
- **R7:** The hardening is **tracker-agnostic**: it lives in the transport-blind adapter / lifecycle-hook layer and applies uniformly to **every adapter — Linear, GitHub, and any future tracker** — never Linear-only. [user]

## Boundaries
<!-- scope: business -->

- **NOT** a rewrite of the tracker-sync bridge (fn-52, shipped) — a reliability hardening of its lifecycle hooks. [inferred]
- **NOT** making the body reconcile deterministic — that legitimately stays an agentic skill. [user: "make ... call a real flowctl sync lifecycle ... or equivalent wrapper" applies to the mechanical parts]
- **NOT** changing the opt-in / opt-out config model (`perEvent`, default-on-after-ceremony) — only how reliably the opted-in events fire and are observed. [inferred]
- Tracker side-effects stay **best-effort / non-fatal** to the primary work loop — observability adds a receipt, never a hard block on a tracker failure. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation

A bridge whose lifecycle hooks silently no-op erodes the whole value proposition — the user believes the tracker mirrors flow state, but PRs land unlinked and issues never move, and the user only finds out by accident (as happened on FLOW-5 and in the GNO-3 Codex session). [user]/[inferred] Making the hooks observable + forcing converts "did the agent remember?" into a checkable property, the same way Ralph's receipts make autonomous state transitions auditable. [paraphrase]/[inferred]

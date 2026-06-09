## Conversation Evidence

> user: "a new quite light weight skill that can be called by / loop in claude code or / goal in codex that checks what the next spec is that is marked as ready (do we have thats status) or the next spec that has a corresponding status in the tracker software configured in a project"
> user: "if you look at our flow, you are conflating spec with plan i think. in our flow, the brunt of the work goes into the spec. the plan is just the agent planning the actual implementation surely"
> user: "we need a new status i think for users that do not have tracker-sync connected, correct? for those that do we need to determine which state equates to the ready state."
> user: "this will mean touching some skills like capture/interview etc to potentially ask them if the spec is ready and the plan skill to check and warn if not ready (soft block), not sure, think it all through, not too complicated"
> user: "this can all be mostly solved with prompting, not scripting and already works well even without loop and goal"
> user: "remember that the docs and flow-next.dev (~/work/flow-next.dev) will need comprehensive updates too" [verbatim prefix]

## Goal & Context
<!-- Source: 60% [user] / 30% [paraphrase] / 10% [inferred] -->

The spec is flow-next's load-bearing artefact and the point where human judgment concentrates — the plan and everything downstream is mechanical agent work. Today a spec has only `open | done`; there is no signal for "the human considers this spec complete enough to hand to an agent." This spec adds a **readiness** signal: a human-owned gate marking a spec ready for autonomous (or confident manual) execution.

It is the entry gate the forthcoming build-loop will consume, but it stands on its own as backlog hygiene — knowing which specs are blessed vs still-draft, and being nudged away from planning a half-baked spec — useful even with no loop in play. Target users: solo devs and teams on flow-next, with and without a tracker connected.

## Architecture & Data Models
<!-- Source: 70% [paraphrase] / 20% [user] / 10% [inferred] -->

A `ready` boolean on the spec record (default `false`), persisted in the spec JSON sidecar and orthogonal to `status` (`open|done`). Readiness has **one local read path** with two write sources depending on config:

- **No tracker** — the human sets `ready` directly (flowctl command, or the capture/interview prompt).
- **Tracker connected** — tracker-sync projects the configured tracker "ready" state (`tracker.readyState`) onto the same local `ready` flag on each sync; the tracker is authoritative for those users.

flowctl owns the field + set/query plumbing; the skills own *when* to set it and *when* to warn (prompting, not scripting).

## API Contracts
<!-- scope: technical -->

- **`flowctl spec ready <id>` / `flowctl spec unready <id>`** — set / clear the flag. [paraphrase]
- **`ready` exposed** in `flowctl specs --json` and `flowctl show <id> --json`; surfaced as a badge in `flowctl list` / `specs` output. [paraphrase]
- **Config key `tracker.readyState`** — records which tracker workflow state maps to readiness, resolved per tracker type (Linear: a workflow-state name; GitHub: a label). [user]

## Edge Cases & Constraints
<!-- scope: technical -->

- Default `false`; pre-existing specs read as not-ready (absent flag). Non-adopters never see readiness surfaced unless they engage it. [inferred]
- For tracker users, each sync re-projects readiness — a local flag edit may be overwritten by the tracker state (tracker authoritative). [paraphrase]
- `capture --rewrite` resets `ready` → `false` (material spec change re-opens the blessing). [inferred]
- Readiness is orthogonal to `status` — a ready spec stays `open` through planning and work. [paraphrase]
- Linear readiness is a state-**name** match layered on the existing `state.type` mapping — a custom "Ready" state typically carries `state.type=unstarted`, which alone cannot distinguish Todo from Ready (same name-override pattern as status-sync). [inferred]
- GitHub issues have no workflow states — for GitHub-tracked projects `tracker.readyState` resolves to a label. [inferred]
- The `ready` flag lives in the committed spec JSON (same placement as `plan_review_status`), so tracker-driven re-projection may produce working-tree changes on sync — accepted, identical to existing status-sync behavior. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A spec carries a `ready` boolean (default `false`), persisted in its record and exposed via `flowctl specs --json` / `show --json`. [paraphrase]
- **R2:** A human can mark / unmark a spec ready via flowctl (`spec ready` / `spec unready`), and the state is visible in spec listings as a badge. [user]
- **R3:** For tracker-connected projects, the configured tracker "ready" state projects onto the local `ready` flag on sync, giving readiness a single local read path. [user]
- **R4:** tracker-sync setup asks which tracker workflow state means "ready" and stores it as `tracker.readyState` (a Linear state name or a GitHub label, per tracker type). [user]
- **R5:** capture and interview offer an optional end-of-authoring prompt to mark the spec ready (default: keep draft). [user]
- **R6:** plan soft-checks readiness — when a spec isn't ready it warns and offers proceed / abort; never a hard block. [user]
- **R7:** The readiness gate is opt-in and invisible to users who never engage it — existing specs and non-loop workflows behave exactly as before. [inferred]
- **R8:** Documentation and the flow-next.dev site are updated to cover readiness — architecture spec-lifecycle, GLOSSARY "Ready" term, flowctl command reference, tracker-sync `readyState` mapping; site pages + both navbars + changelog. [user]

## Boundaries
<!-- scope: business -->

- This spec adds the **readiness signal only**. The build-loop and ship-loop skills that consume it are separate, forthcoming specs (this one is their shared dependency). [user]
- No new value is added to the `status` enum — `open|done` is unchanged; readiness is a separate orthogonal flag. [paraphrase]
- No automatic readiness inference — readiness is always an explicit human action or a tracker-state projection, never the agent judging a spec "looks ready." [inferred]
- Parallel execution, PR merge, and release are out of scope (other specs). [paraphrase]

## Decision Context
<!-- scope: both -->

Readiness is a **flag, not a new `status` value** — `status=open|done` is checked throughout flowctl and stays clean, while readiness is orthogonal and persists through planning and work. The gate is **opt-in / invisible-by-default** so the large body of existing specs and non-loop users are undisturbed. The signal is deliberately **human-owned (or tracker-projected), never agent-inferred** — readiness is the human's gate, the place intent concentrates, because the spec carries the weight and the plan is mechanical agent work. flowctl owns storage; skills own the workflow — the standard skill + thin-plumbing split. [strategy:Ralph autonomous mode]

## Strategy Alignment
<!-- STRATEGY.md populated 2026-05-16 -->

- Aligns with the **Ralph autonomous mode** track — readiness is the human-blessed entry gate that lets a host-driven loop execute a spec unattended while the human keeps control of *direction*. [strategy:Ralph autonomous mode]
- Aligns with the approach principle *"the host agent IS the intelligence; flowctl provides thin atomic helpers"* — readiness is a thin flowctl field; all judgment is skill prompting. [strategy]
- No conflict with *"Not working on: built-in CI runners / SaaS"* — readiness is in-repo metadata only.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1–R8 | TBD — populate via /flow-next:plan |

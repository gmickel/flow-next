---
satisfies: [R4]
---
# fn-125-cursor-scout-pin-wiring-consume-the.1 Ratify + single-source the Cursor scout-routing contract

## Description
Ratify + single-source the Cursor scout-routing contract. Add a shared reference `plugins/flow-next/references/read-only-scout-routing.md` defining the Cursor-only dispatch contract (mirror the fn-123 host-review resolution shape, but COST-only fail-OPEN semantics, NOT fail-closed): Cursor-host activation, marker-bounded AGENTS.md routing-block lookup, exact `read-only scouts` row selection, opaque model-argument pass-through, tool-enforced read-only, session-model fallback. Narrow setup's current "any read-only Explore-class subagent" promise (flow-next-setup/workflow.md) to the NAMED Plan/Prime scout fan-outs (+flow-gap-analyst); exclude ad-hoc Capture/Interview/Audit/Prospect investigation subagents and all reviewer paths. Leave templates/model-routing-snippet.md unchanged (serves the non-Cursor scaffold). Update test_setup_cursor_host.py.

DECISION GATE (spec R4): this task's plan-review must explicitly ratify CONSUME (wire the pin) vs DROP (remove the scaffold row + document inherit). Codex plan recommends CONSUME but flags the real tension: a single cheap Cursor pin flattens Prime's fast(haiku)-vs-judgment(sonnet) split. If review rejects reliable consumption, the approved alternative is ATOMIC DROP (remove SCOUT_PIN + row/rule + claims); no partial wiring.

## Acceptance
- Plan-review explicitly approves CONSUME (incl. named-scout eligibility + Cursor-host signal) OR mandates atomic DROP.
- Shared reference defines: Cursor-only activation, marker-bounded routing-block lookup, exact row selection, opaque model pass-through, read-only enforcement, session-model fallback.
- Generic investigation subagents + every reviewer path explicitly excluded; setup producer contract cites the reference and drops the blanket-pin promise.
- Reference <500 LOC; large workflows link rather than duplicate.
- test_setup_cursor_host / test_model_routing_scaffold green; host-review + non-Cursor assertions unchanged.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

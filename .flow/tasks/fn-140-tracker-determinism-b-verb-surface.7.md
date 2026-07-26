---
satisfies: [R19]
---
# fn-140-tracker-determinism-b-verb-surface.7 Lifecycle facade: tracker sync --op push|pull|reconcile|comment

## Description
Build the facade callers actually invoke. The granular verbs are the mechanism; without this, every calling skill would have to compose them in prose - which is exactly what this batch removes, and would make spec C's behavior-preserving teardown impossible.

```
flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <perEvent-key> [--flow-file F] [--body-file B]
```

The four ops match the existing `perEvent` vocabulary exactly (`off | pull | push | reconcile | comment`). Composition is tabulated in the epic: required/forbidden inputs and the ordered internal sequence per op. **Receipts do not stack** - internal granular calls run with receipts suppressed and the facade writes exactly one aggregate, event-tagged receipt whose status is the worst of its steps. A partial success returns `success: false` with `data.completed_steps`. Re-running is idempotent.

**MCP is the explicit exception**: flowctl cannot call MCP, so a facade `push` on Linear's MCP rung returns `class: external_action_required` with the payload for the agent, completed via `persist-external`. Single-call conformance is scoped to shell-reachable transports.

Judgment-bearing content is passed **in** as a file. The facade never renders a body, never resolves a merge, never writes comment prose.

## Acceptance
- [ ] All four ops implemented; conformance scoped to shell-reachable transports
- [ ] MCP rung returns `external_action_required` with an actionable payload, completed via `persist-external`
- [ ] Required/forbidden input matrix enforced per op
- [ ] `push` on an unlinked spec performs create-if-unlinked, then the sequence
- [ ] Comment marker + dedup reproduce current behavior (no duplicate on re-run)
- [ ] Exactly ONE aggregate receipt per invocation; internal granular calls suppress theirs
- [ ] Partial success returns `completed_steps` so a resume is informed
- [ ] Re-running any op is idempotent (create-if-unlinked no-ops, comment marker dedups)
- [ ] Conflict and degradation surface structurally, not as prose
- [ ] Facade composes NO judgment content; body/comment text is always an input file
- [ ] A caller can replace a today-dispatch with one facade call and observe identical tracker state

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

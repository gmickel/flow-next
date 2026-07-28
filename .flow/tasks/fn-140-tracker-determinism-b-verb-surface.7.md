---
satisfies: [R19]
---
# fn-140-tracker-determinism-b-verb-surface.7 Lifecycle facade: tracker sync --op push|pull|reconcile|comment

## Description
Build the facade callers actually invoke. The granular verbs are the mechanism; without this, every calling skill would have to compose them in prose - which is exactly what this batch removes, and would make spec C's behavior-preserving teardown impossible.

```
flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <perEvent-key> \
  [--flow-file F] [--body-file B] [--comments-file C] [--source-body-file S]
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
Lifecycle facade shipped: tracker sync <spec-id> --op push|pull|reconcile|comment --event E (grok-4.5, 3 codex rounds).

One call replaces a touchpoint dispatch after the skill prepares any judgment
inputs. Push = create-if-unlinked -> sync-body(push) -> gate-derived status ->
dependency projection. Pull = one claimed durable-validated issue read,
readiness projection, current-comment validation, exact final-local-form
validation, paired-base commit, then status reconciliation. Reconcile performs
the same pull-side readiness/comment/final-form checks, projects dependencies
even when body merge later conflicts, then validates the pre-merge remote
snapshot before sync-body/status. Comment = create-if-unlinked ->
flow-next:sync marker dedup via comment-list BEFORE any post
(issue+evt+evidence; fn-89 retry rule) -> comment-add.

Receipts do not stack: write_receipt=False seams cover status, sync-body, and
relate; exactly one aggregate event-tagged receipt records the worst step.
Partial success returns success false + completed_steps; retries are
idempotent. MCP returns external_action_required with the actionable payload
and zero tracker requests. Degradation stays structured. The strict input
matrix now carries final Flow, source/outgoing tracker body, and normalized
comment snapshot separately so the facade cannot commit a stale or mismatched
base.

Rounds: 2 findings -> 1 -> SHIP.
## Evidence
- Commits: d93dc2c5, 47126a19, c29b0cbb
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_facade test_tracker_wire test_tracker_capabilities test_tracker_conformance test_tracker_syncbody test_tracker_status test_tracker_distribution test_flowctl_surface test_prompt_text_pinned -q (401 tests); live GitHub/GitLab/Linear/Jira facade push, dependency, comment, readiness, and pull round-trips with disposable cleanup; python3 scripts/run_tests_parallel.py; uvx ruff@0.16.0 check .
- PRs: #246

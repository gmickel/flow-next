---
satisfies: [R2, R3, R5, R11, R13, R17]
---

## Description
The **agentic heart**, in a NEW `references/backlog-mode.md` (R11). Host-agent workflow:
- **Selection (pull-before-scan, finding #7):** Phase 1 FIRST runs an unattended tracker-sync **pull/reconcile** for linked items (no-op if inactive), THEN calls `flowctl ready --all` (flow facts) and unions the **tracker-only** promoted issues via tracker-sync's **`list-open`** op (`listOpenIssues`, .2; flowctl has no tracker transport). **Filter is the exact `tracker.readyState`** (round-2 #4). **When `tracker.readyState` is unset, `list-open` no-ops** (no promoted-lane filter) and backlog mode runs the **flow-ready specs only** — the flow `ready` flag needs no tracker (round-3 #4). **Skip any item carrying a `status=open` parked question** (finding #5; for tracker-only items the parked state is read from the tracker comments). Pick the top actionable item.
- **Dep-ordering (mixed flow+tracker, finding #12 + round-2 #5):** flow deps from `blockedBy` (`ready --all`). **Tracker deps are NOT in the `issue` struct** — `list-open` returns issue-only, so pilot then calls **`listIssueRelations` per tracker issue**, normalizes the edges, and feeds them (with the flow `blockedBy` edges) into the **`flow-next-deps` jq topo-sort** (reuse — no graph engine). A cycle/deadlock ⇒ `ASKED`/`BLOCKED`, never spin.
- **Agentic triage — host's read, NO flowctl judgment (R3, finding #4):** classify by the **EXPLICIT readiness signal FIRST**. **Unready items skipped silently.** Signalled items route: workable → advance; ready-but-thin/ambiguous → `ask`; dep-unsatisfied → `BLOCKED`; needs-human → `ask`. **A tracker-only promoted item (no flow spec) always triages to `needs-spec`** (round-2 #1) → the question goes to the **tracker comment ALONE** ("this promoted ticket has no flow spec — run capture/interview"); **never a spec stub** (forbidden authoring). **Its parked/answered state lives in the tracker** (scan comments for `flow-next:question id=… status=open` + a matching `flow-next:answer id=…`), not a spec anchor — no spec import/flip until capture/interview later creates a spec (round-3 #1). `needs-spec` is always a *promoted* item, never an un-promoted idea. Completeness read may only *withhold*, never *force*.
- **Full-auto default (R5):** workable + dep-clear + unambiguous → advance; optional **`pilot.gateClasses: [<class>]`** (sibling key) force-surfaces named classes.
- **Transport-blind multi-tracker (R13):** `list-open` + `question` ops only; v1 Linear+GitHub, GitLab/Jira (fn-69/70) inherit. No tracker-specific code in pilot.
- **Spec-first floor (R17):** no tracker reachable → spec-only `## Open Questions` (when a spec exists) + a one-line "enable X to mirror" note; never block.

**Size:** M-L · deps .1, .2
**Files:** `plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md` (NEW)

## Approach
- File pattern: model on `flow-next-work/references/codex-delegation.md`.
- Selection extends pilot's Phase-1 SELECT (`workflow.md:56-91`); reuse `flow-next-deps/SKILL.md` topo-sort; workable items route into pilot's CLASSIFY (`workflow.md:93-195`) unchanged.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:56-91` — SELECT (extend) + `:93-195` — CLASSIFY
- `plugins/flow-next/skills/flow-next-deps/SKILL.md` — jq topo-sort to reuse
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md` — `list-open` / `listIssueRelations` / `question` (from .2)
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` — reference-file pattern

## Key context
**Flow-swarm boundary:** ONE smarter tick — NO polling loop / trigger / daemon / parallel-worktree (control plane = flow-swarm fn-94/99); the host `/loop`·`/goal` owns repetition. STOP-at-make-pr enforced in .4. DORA grounds surface-don't-block.

## Acceptance
- [ ] `references/backlog-mode.md` authored: pull-before-scan selection (reconcile → `ready --all` ∪ `list-open` at exact `readyState`, skip `status=open` parked items), mixed dep-order (flow `blockedBy` + per-issue `listIssueRelations` → flow-next-deps topo-sort; cycle → ASKED/BLOCKED), agentic triage (unready skipped; signalled → workable/ready-but-thin/needs-spec/blocked/needs-human; **tracker-only → needs-spec via tracker comment only, never a spec stub**), full-auto + `pilot.gateClasses`, transport-blind (Linear+GitHub v1), spec-first floor.
- [ ] triage is the host agent's read — no deterministic scorer / regex grader / flowctl judgment field.
- [ ] dep-order reuses the flow-next-deps topo-sort (no new graph engine); tracker deps sourced via `listIssueRelations` per issue (not the `issue` struct); cycle surfaced, never spun.
- [ ] no daemon / polling / trigger-handler prose — one smarter tick.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

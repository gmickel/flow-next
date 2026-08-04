---
satisfies: [R3, R4]
---

## Description

Tracker readiness projection: the `tracker.readyState` config key, the ceremony question that sets it, and the pull-side projection step that maps the configured tracker state onto the local `ready` flag.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (config default only), `.flow/bin/flowctl.py` (re-copy — byte-equivalence must hold after EVERY flowctl.py touch), `plugins/flow-next/skills/flow-next-tracker-sync/steps.md`, `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md`, `references/linear-mcp.md` (one line), `references/github.md`

## Approach

Per spec §Resolved at planning:
- **Config**: declare `"readyState": None` at the tracker TOP level in `get_default_tracker_config` (:1045) — sibling of `conflictTiebreak`/`staleAfterHours`, NOT under `perTracker` (single scalar). Note `statusMap` is documented-but-absent from defaults — leave it as-is (deliberate; don't fix here).
- **Ceremony** (steps.md Phase 1 step 4, :43-59): after the existing config writes, ask "which workflow state means ready-for-work?" — Linear: discover states via `list_issue_statuses` (id/name/type), lead-with-recommendation (a state named like Ready/Next, else skip), validate via `get_issue_status`; GitHub: a label name, pre-create with the 422-already-exists guard (`gh label create` pattern in github.md:154-156). Skippable — readiness is optional; skipping leaves `readyState: null`.
- **Projection** (status-sync.md, after the status-normalization step :228-238): when `readyState` is set, compare Linear `state.name` case-insensitive/trimmed (names non-unique + renamable; type alone can't distinguish Todo from Ready) or GitHub `labels[].name` → derive desired local `ready` → call `flowctl spec ready/unready` (idempotent, .1). **GitHub semantics:** label present on the issue → ready=true; label ABSENT → ready=false (a normal state, never an error/noop); only an unresolvable repo label or invalid config produces the warn path. **Emit an `--event`-tagged receipt only when the flag actually CHANGES** (silent on echo — mirrors lastSyncedAt semantics); configured-name-not-found → warn `noop` receipt + flag untouched + sync continues (graceful degradation, status-sync unmapped-state precedent :222-248). One-way: NEVER write readiness back to the tracker. Readiness receipts are local-only — never posted as tracker comments (auto-linkify memory).
- Linear GraphQL rung: `workflowStates(first:100, filter:{team:...}){nodes{id name type}}` — every nodes connection needs `first:` (memory).

## Investigation targets

**Required:**
- `.flow/specs/fn-58-spec-readiness-signal-ready-flag.md` §Resolved at planning
- `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md:193-251` — the name-override + unmapped-surface pattern to extend
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md:25-60` — ceremony Phase 1
- `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md:107-156` — label namespace + pre-create guard

**Optional:**
- `references/linear-mcp.md:138-144` — list_issue_statuses shapes
- `plugins/flow-next/scripts/flowctl.py:1045-1080` — tracker config defaults

## Acceptance

- [ ] `config get tracker.readyState` returns a clean null on fresh repos; ceremony asks + stores it (skippable)
- [ ] Pull-side projection: Linear name-match (case-insensitive, trimmed) / GitHub label-match sets the local flag via the idempotent .1 commands
- [ ] Change-only receipts (`--event`-tagged); not-found → warn noop receipt, flag untouched, sync continues
- [ ] No outbound readiness write; no readiness text in tracker comments
- [ ] GitHub: label-absent projects ready=false (normal), only unresolvable-config warns; dogfood `.flow/bin/flowctl.py` re-copied byte-identical
- [ ] Full suite green; ceremony + projection prose passes sync-codex validators (regen deferred to .4)

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: tracker.readyState config + pull-side readiness projection are live (this repo runs readyState=Todo; readiness soft-checks read it). No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs:
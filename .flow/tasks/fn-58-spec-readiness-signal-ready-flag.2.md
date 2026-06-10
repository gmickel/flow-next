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
Added the tracker readiness projection plumbing (fn-58 R3/R4): `tracker.readyState` config default (null, tracker top level) in flowctl with tests, the skippable discovery-ceremony question that sets it (Linear state-name discovery/validation via list_issue_statuses/get_issue_status, GitHub label with 422-guarded pre-create), and the pull-side projection in status-sync.md that maps the configured tracker state onto the local `ready` flag via the idempotent fn-58.1 toggles — change-only --event-tagged receipts, stale-config warn-noop with flag untouched, strictly one-way pull with local-only receipts. rp impl-review verdict: SHIP (first pass, no findings).
## Evidence
- Commits: 9b80f9756b404aa416fee1c2460b9ee0b18cfd0d
- Tests: cd plugins/flow-next && python3 -m unittest discover -s tests (1047 tests OK), python3 -m unittest tests.test_tracker_config -v (10 tests OK incl. new readyState assertions), flowctl config get tracker.readyState --json -> null on fresh + existing repo; set/get round-trip, cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py (byte-identical), bash scripts/sync-codex.sh (all validators pass; mirror regen reverted, deferred to fn-58.4)
- PRs:
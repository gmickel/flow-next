---
satisfies: [R1, R2]
---
# fn-140-tracker-determinism-b-verb-surface.1 Wire verbs with locator addressing, all four adapters

## Description
Implement the wire verb group through spec A's injected executor: `read`, `update`, `comment-add/list/update/delete`, `label`, `assign`, `list-open`.

Every verb takes a **locator** `{durable, display}`, not an id. A durable id cannot address GitHub (REST needs the issue `number`, durable key is `node_id` - `github.md:207` says "Never the `number`") or GitLab (needs project-local `iid`, durable key is global `id`). Responses carry the durable id back and the adapter validates it against the locator, which catches a project move.

`comment-update`/`comment-delete` require the parent locator: GitLab and Jira both need issue AND comment id.

Wire verbs touch no local state and write no receipt.

## Acceptance
- [ ] All wire verbs work on GitHub, GitLab, Linear, Jira via fake transport
- [ ] **Write verbs validate BEFORE mutating** via a pre-mutation parent read; mismatch aborts with `class: conflict`
- [ ] Response-side validation ONLY where the response carries parent identity; otherwise marked "parent identity not available", not faked
- [ ] `attach-get` and `list-open` are context-free and take NO locator (`attach`/`attach-get` IMPLEMENTATIONS land in task .4 with the capability gates; this task pins the contract for the verbs it ships - R1 completes at .4)
- [ ] Read-only verbs may validate on response alone
- [ ] `comment-update`/`comment-delete` require the parent locator
- [ ] `GET /issues` on GitHub filters pull requests (the `pull_request` key)
- [ ] No wire verb writes a receipt or local state

## Done summary
Wire verb group shipped on the injected executor: read / update / comment-add|list|update|delete / label / assign / list-open, all four adapters, via grok-4.5 (cursor bridge) implementation with host review on top.

Locator {durable, display}; every WRITE does a pre-mutation parent read (display-addressed, durable-compared - host fixed grok's vacuous durable-by-durable reads on Linear/Jira) and aborts class conflict before any mutation. GitHub+Linear comment mutations additionally verify comment->parent ownership (globally-addressed comment ids could mutate another issue's comment). Linear mutations require success is True. Response-side identity only where it exists (GitLab noteable_id, Linear issue{id}); GitHub/Jira comment responses and Jira 204 write responses honestly not_available. GitHub list-open filters PRs; GitLab filters system notes, state=opened. Pagination drained on every list surface (REST page loop / GraphQL cursors / Jira startAt) with an honest truncated flag. No receipts, no local state. wire/ package split (<500 LOC per file). attach/attach-get land in .4 per spec decomposition (noted on task; R1 completes there).

3 codex verdict rounds (several transport flaps refunded - codex intermittently returned empty output; watch item recorded): round 1 five findings, round 2 one, round 3 SHIP.
## Evidence
- Commits: a583a757, db88c8aa, 90ab0671
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_wire -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs:
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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

---
satisfies: [R15, R17, R20]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.10 Active docs, skill contracts, mirror, and docs-site repair

## Description
Perform a fresh active-source CLI/payload reference repair after all code changes.

Known confirmed floor remains: README epic aliases/migrate-rename; nonexistent config toggle; Ralph unblock/update; global --version/setup; unnamespaced review commands; strategy's bare flowctl and nonexistent list; export --section/review_receipts claims; deleted RP pick-window/builder; and post-alias config wording. Exclude historical specs/tasks/changelog and named frozen eval fixtures.

Preserve flow-next 3.1.0 truth while editing: plugin mode, plugin-bin launcher, flowctl usage, setup-mode, canonical plugins/flow-next/templates/usage.md, slim snippet/pre-check contracts, agent_docs/setup-modes.md, and paired Codex mirror transforms/guards. Add a scoped executable-snippet/reference gate. Update root/docs-site Unreleased entries; no version bump.

Complexity: 58/100.

Quick commands:
- ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
- documentation/prose contract tests including fn-121 contract tests
- cd ~/work/flow-next.dev && pnpm build
## Acceptance
- [ ] Active docs/skills contain no deleted command, flag, alias, or payload-field instructions.
- [ ] Strategy uses its resolved FLOWCTL path everywhere canonical prose requires it.
- [ ] Smoke labels describe the operation actually exercised.
- [ ] Scoped parity gate validates executable command snippets while excluding historical/frozen records.
- [ ] Plugin-mode, plugin-bin, flowctl usage/setup-mode, canonical usage template, slim snippet, and mirror transforms remain accurate and tested.
- [ ] Canonical changes regenerate the Codex mirror twice idempotently with all guards green.
- [ ] README/plugin docs/agent docs and flow-next.dev reflect Python 3.11, startup behavior, and 3.1.0 setup reality.
- [ ] Root and docs-site Unreleased entries are staged; docs site builds; no version manifest changes.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

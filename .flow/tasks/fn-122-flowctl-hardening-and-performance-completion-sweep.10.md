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
Repaired the active post-3.1 command and payload contract across README, plugin/agent docs, canonical skills, generated Codex mirror, smoke labels, and flow-next.dev. Added a scoped executable-reference gate covering canonical and generated Markdown plus Codex agent TOML; it validates registered command families, removed surfaces, strategy FLOWCTL resolution, cognitive-aid payload fields, CE direct-exploration commands, and canonical smoke labels. Made RepoPrompt Community Edition the primary documented/direct CLI path while retaining Classic only as Flow-Next's final wrapper fallback. Staged root and public-site Unreleased entries without version changes. Public docs commit: e4d5f44.

Verification: 134 focused fn-121/fn-122 contract tests passed; sync-codex ran twice idempotently; plugin validation passed; isolated deterministic shell smoke passed 131/131; flow-next.dev Astro check/build passed with 0 diagnostics and 74 pages; Copilot implementation review reached SHIP after one fix round. A full-PATH smoke additionally passed 135/136: Codex plan-review and both Copilot live reviews passed, while one Codex impl-review call returned exit 2. That backend-specific anomaly is retained for task .11's explicit integration reproduction.
## Evidence
- Commits: 4194eb6e
- Tests: ./scripts/sync-codex.sh && ./scripts/sync-codex.sh, cd plugins/flow-next/tests && python3 -m unittest test_cmd_usage test_setup_block_helper test_setup_mode_stamp test_precheck_mode_contract test_startup_bootstrap test_skill_prose_diet test_template_canonical test_flowctl_surface test_sync_check -q (134 passed), claude plugin validate plugins/flow-next, PATH=/usr/bin:/bin PYTHON_BIN=/opt/homebrew/bin/python3 plugins/flow-next/scripts/smoke_test.sh from /tmp (131 passed, 0 failed; optional model CLIs skipped), cd /Users/gordon/work/flow-next.dev && bun x pnpm build (Astro check 0 diagnostics; 74 pages built), flowctl copilot impl-review fn-122...10 --base f7d24e83 (SHIP after one fix round)
- PRs:
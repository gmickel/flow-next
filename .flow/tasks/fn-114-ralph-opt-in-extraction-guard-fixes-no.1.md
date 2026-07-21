# fn-114-ralph-opt-in-extraction-guard-fixes-no.1 No-default-install: hooks.json deleted, agent-driven registration

## Description
Ralph no-default-install: plugin hooks deleted, registration becomes agent-driven ralph-init prose.

**Size:** M
**Files:** plugins/flow-next/hooks/hooks.json (DELETE), plugins/flow-next/.claude-plugin/plugin.json (hooks ref if any), plugins/flow-next/skills/flow-next-ralph-init/* (registration prose), plugins/flow-next/skills/flow-next-setup/workflow.md (Ralph ask), plugins/flow-next/skills/flow-next-uninstall/* (removal parity), plugins/flow-next/docs/platforms.md, tests

### Approach

- Read spec section A fully. Delete plugins/flow-next/hooks/hooks.json and any plugin-manifest reference; fresh installs register ZERO hooks.
- ralph-init prose: instruct the host agent to MERGE the four hook entries into the project's .claude/settings.json via Read+Edit (never clobber existing hooks, idempotent re-run; Claude Code's project-hooks trust prompt is the consent gate). Droid: cover the Factory-equivalent settings path in prose (verify the current path against platforms.md knowledge; if uncertain state the caveat inline). HARD BOUNDARY: no new flowctl subcommand, zero hook machinery in Python.
- Setup: AskUserQuestion whether to enable/keep Ralph (default No; sync-codex rewrites the ask for the mirror). Yes -> point at ralph-init. No -> agent removes any flow-next hook entries found in .claude/settings.json and notes the scripts/ralph/ scaffold can be deleted (ask before deleting).
- Uninstall prose: same agent-driven hook-entry removal step.
- Tests: prune/re-pin anything asserting the plugin ships hooks.json; add a guard test asserting the plugin manifest carries no hooks entry and plugins/flow-next/hooks/ is absent.
- Dual-copy untouched unless flowctl references hooks.json (check). sync-codex x2. NO git commands, no flowctl start/done, no em dashes.

### Acceptance

- [ ] plugins/flow-next/hooks/hooks.json gone; manifest carries no hooks; guard test pins it
- [ ] ralph-init prose owns registration (merge, idempotent, consent-gated); setup asks (default No) with removal path; uninstall parity
- [ ] platforms.md notes the per-host hook installation difference
- [ ] Focused: --pattern "test_ralph*.py" + any hooks-asserting suites green; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
Plugin-level hooks are GONE: plugins/flow-next/hooks/hooks.json deleted, no manifest hooks key, fresh installs register zero hooks - pinned by test_no_default_hooks (5 assertions: no dir, no manifest key, registration prose present, setup default-No + removal path, uninstall strip). Registration is agent-driven ralph-init prose per platform: Claude/Grok merge fingerprinted guard entries into .claude/settings.json (project trust prompt = consent gate), Droid .factory hooks with settings fallback, Codex subset (shell Pre/Post + Stop; no file matchers/SubagentStop), Cursor scaffold-only (hook-schema mismatch documented). Setup asks Ralph enable/keep on fresh AND re-runs (default No; No strips fingerprinted entries and offers scaffold cleanup ask-before-delete); uninstall carries the same removal step; cursor installers stop shipping hooks. Delegate doubts routed within plan: codex mirror hooks generation -> .2, ralph.md + checklist rows -> .4, Droid file-matcher body -> .3, setup-run-vs-point -> accepted (default-No is the protective part). Full parallel suite 86 files / 1858 tests / 0 failures / 70.3s; sync-codex x2; no flowctl changes (dual-copy untouched).
## Evidence
- Commits: 6cce75e2bd29303e3400d26ad6f7bada490f29e6
- Tests: python3 scripts/run_tests_parallel.py (86 files, 1858 tests, 0 failures, 70.3s), test_no_default_hooks.py 5 green, test_ralph*.py 72 green
- PRs:
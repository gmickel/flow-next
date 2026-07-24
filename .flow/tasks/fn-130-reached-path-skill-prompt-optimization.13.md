# fn-130-reached-path-skill-prompt-optimization.13 Prevent recursive completion-review orchestration

## Description
Harden the generated completion-review prompt so a backend subprocess acts as
the terminal reviewer. It must inspect the supplied spec and implementation
directly instead of invoking the Flow-Next coordinator skill, another
`flowctl *-review` command, or another reviewer.

## Acceptance
- [ ] The completion-review prompt begins with an explicit terminal-reviewer role override.
- [ ] The override forbids Flow-Next skill invocation, nested review commands, delegation, and reviewer subprocesses.
- [ ] Codex, Copilot, and Cursor completion reviews receive the override through their shared prompt builder.
- [ ] Regression tests pin the override and rendered prompt fixtures.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_template_parity test_backend_spec test_cursor_review_commands -q
```

## Done summary
Added a terminal-reviewer override at the shared completion-review prompt boundary so Codex, Copilot, and Cursor review directly without invoking Flow-Next skills, nested review commands, delegation, or reviewer subprocesses. Pinned the rendered prompt and refreshed the bootstrap checksum.
## Evidence
- Commits: b56d21ce
- Tests: cd plugins/flow-next/tests && python3 -m unittest -q test_review_prompt_template_parity test_backend_spec test_cursor_review_commands, cd plugins/flow-next/tests && python3 -m unittest -q test_startup_bootstrap test_review_prompt_template_parity, python3 scripts/run_tests_parallel.py (125 files, 2287 tests, 0 failures, 0 errors, 3 skipped), ./scripts/sync-codex.sh twice (idempotent, 28 skills/22 agents)
- PRs:
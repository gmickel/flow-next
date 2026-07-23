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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

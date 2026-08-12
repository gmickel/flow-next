---
satisfies: [R1, R2, R5]
---
# fn-186-worktree-kit-non-interactive-cleanup-no.1 worktree.sh: non-interactive cleanup (names + --yes), EOF-guarded reads, --no-track create; regression tests

## Description
In plugins/flow-next/skills/flow-next-worktree-kit/scripts/worktree.sh: (1) R1 - cleanup accepts 'cleanup <name>... [--yes]': parse "${@:2}" into names + a --yes flag (any other leading-dash token fails usage); names given skip the interactive name prompt; run the y/N confirmation only when stdin is a TTY ([[ -t 0 ]]); non-TTY with names but no --yes -> fail naming the remedy ('pass --yes to remove without a terminal' shape); non-TTY with no names -> fail 'no terminal and no names given'; both read invocations EOF-guarded (read -r x || fail ...) so the script never dies inside a bare read; interactive no-arg behavior unchanged. (2) R2 - the new-branch create path (git worktree add -b) passes --no-track; the existing-branch path unchanged. (3) R5 - regression tests in plugins/flow-next/tests/test_worktree_kit.py matching its existing harness style: cleanup </dev/null with no names exits non-zero with the diagnostic on stderr; 'cleanup <name> --yes' non-interactively removes a registered worktree; 'cleanup <name>' non-TTY without --yes refuses with the remedy token; a branch created via create has no upstream (git rev-parse --abbrev-ref @{upstream} fails). Pin contract tokens, not sentences. Keep worktree.sh a single self-contained script; bash -n clean.

## Acceptance
R1, R2, R5 met; cd plugins/flow-next/tests && python3 -m unittest test_worktree_kit -q green; bash -n clean.

## Done summary
worktree.sh: cleanup now takes `cleanup [<name>...] [--yes]` with TTY-only prompts and EOF-guarded reads (loud failures name the remedy); the new-branch create path passes --no-track. 5 regression tests incl. a mutation-verified no-upstream pin. bash -n, ruff, suite green (8 tests).
## Evidence
- Commits: 389d1387
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_worktree_kit -q, bash -n plugins/flow-next/skills/flow-next-worktree-kit/scripts/worktree.sh
- PRs:
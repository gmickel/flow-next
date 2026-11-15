---
satisfies: [R9]
---
# fn-326-9110-pre-release-fixes-for-issue-start.3 install-codex.sh deletes nothing outside CODEX_HOME when its path has spaces

## Description
install-codex.sh cleans old agents with grep -rl ... | xargs rm -f; a CODEX_HOME containing a space is split by xargs and the second half resolves against the current directory, so running test_codex_config_merge from plugins/flow-next deletes that directory's codex/agents/*.toml. Fix with NUL-separated output (grep -lZ / xargs -0) or a quoted loop. Write the failing test first: run the installer with a CODEX_HOME containing a space from a directory holding a sentinel codex/agents/*.toml and assert the sentinel survives.

Touches: scripts/install-codex.sh, plugins/flow-next/tests/test_codex_config_merge.py

## Acceptance
R9 holds: the sentinel test fails on the old script and passes on the fix; ls plugins/flow-next/codex/agents | wc -l still reads 21 after running the test from plugins/flow-next.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

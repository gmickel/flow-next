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
install-codex.sh now removes old generated agents in a quoted per-file loop instead of `grep -rl | xargs rm -f`, so a CODEX_HOME containing a space no longer splits into a cwd-relative path that deleted the caller's codex/agents/*.toml (R9).

Test: `test_real_installer_recovers_and_is_idempotent` (spaced `work codex` home, two installer runs) now runs the installer with cwd set to the temp home and asserts a sentinel `codex/agents/agents-md-scout.toml` there survives. Committed alone first (df233db54) and failed on the old script (`AssertionError: False is not true` at `self.assertTrue(sentinel.exists())`); passes after the fix (741cf8058). The cwd pin also means the test can no longer touch the repo's own agents from any working directory.

Base/head from `plugins/flow-next` (measured, in throwaway `git archive` copies, never the workspace): base `suite_rc=1`, `FAILED (failures=1, errors=3)`, agents 21 -> 0; head `suite_rc=0`, `OK`, agents 21 -> 21. Workspace `ls plugins/flow-next/codex/agents | wc -l` = 21 at the end.

Gates (measured, from workspace root): test_codex_config_merge, test_install_codex_legacy_cleanup, test_codex_hooks_normalize, test_codex_flow_dispatch, test_install_opencode, test_tracker_distribution all OK; `uvx ruff@0.16.0 check` on the test file clean; `bash -n scripts/install-codex.sh` clean. baseline: green via handoff (verified at a59e4637 by conductor: test_codex_config_merge).

Defect-pattern sweep: the only `| xargs rm` on the installer surface was this line; sync-codex.sh's xargs uses operate on repo paths and are out of scope. Used a loop rather than `grep -lZ`, since `-Z` means decompress on macOS BSD grep.

Tier: session (jev moderate 0.88) at default effort (model: claude-opus-5-5)

stage: impl-review - skipped(policy: parallel-wave - conductor owns review after integration)

stage: impl-review - ran codex single reviewer SHIP (model: gpt-6.1-sol)
stage: plan-sync - skipped(config: planSync.enabled=false)
Tier: session (jev moderate 0.88) at default effort (model: claude-opus-5-5)
## Evidence
- Commits: d09d0da70e171e095e67fee335227a0b371087e4, 4c4e65bc8cff7679f90308fc10134aee74844dc2
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_codex_config_merge.py' (+ legacy_cleanup, hooks_normalize, codex_flow_dispatch, install_opencode, tracker_distribution)
- PRs:
---
satisfies: [R3]
---
# fn-192-state-contract-honesty-fresh-clone.2 done/block: modified_paths manifest + dirty-tracked stderr advisory

## Description
R3: cmd_done (flowctl.py ~:34817-34837) gains "modified_paths": [str(task_spec_path)] in its --json success payload (additive; nothing pins that dict), and after the atomic_write, when the path is tracked and now dirty (git diff --quiet -- <path>; repo root already resolved), print ONE stderr advisory naming the path and that the receipt belongs in a commit (shape precedent: print_status_source_advisory ~:1094). Exit code unchanged. Apply the same manifest+advisory to cmd_block's identical write-tracked-then-runtime shape (~:34875-34890). FORBIDDEN: any git add/commit/amend from inside flowctl; changing write ordering; touching validate (task 1 owns it). R5(iv-v) tests: done --json contains modified_paths; advisory on stderr when dirty; no advisory when the tree is clean for that path. Find the right existing suite (grep tests/ for cmd_done coverage) and match its harness.

## Acceptance
R3 + R5(iv-v) met; focused suites green; Ralph/pilot guard behavior unchanged (exit codes + JSON status keys untouched); ruff clean.

## Done summary
done/block --json payloads gain modified_paths (the tracked file the command wrote); one stderr advisory when that file is tracked-and-now-dirty (single git diff --quiet spawn, returncode-1-only contract - untracked/clean/no-repo degrade to silence). New focused suite test_done_tracked_write.py (9 tests) + 307 neighboring tests green.
## Evidence
- Commits: eebda874
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_done_tracked_write -q
- PRs:
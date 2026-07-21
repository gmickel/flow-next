---
satisfies: [R17, R18, R19, R20, R21]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.11 Integration benchmark, cross-platform gate, and completion evidence

## Description
Run the final integrated verification once all tasks land. Collect the reproducible pre/post benchmark report for ordinary and specialized paths, explicitly including plugin-bin/copy help, flowctl usage, setup-mode, config, list, status, specs, prime, export, memory, cascade, and pilot. Compare deterministic operation counts and investigate every >10% regression.

Exercise Python minimum/latest, Windows locking/launcher coverage, plugin/copy modes, plugin-bin, mirrors, dogfood and Ralph copies, full Python suite, shell smokes, plugin validation, and docs build. Prepare completion-review evidence with commits, exact commands/results, benchmark tables, retained/deferred findings, and clean-worktree state. Do not bump or release.

Run a bounded live RepoPrompt Community Edition smoke on this macOS host with CE installed. Record the resolved executable/version and prove CE wins when discontinued Classic is also installed. Against one deliberate review workspace, exercise all supported `flowctl rp` wrappers (`setup-review`, prompt set/get, selection add/get, chat send, and prompt export). Invoke `setup-review --create` twice, capture window inventories before/after, and prove the second call reuses the same numeric CE window rather than cloning the workspace; tabs may differ. Use a minimal chat prompt and validate transport/session identifiers, not answer quality. Keep exports temporary and record any intentional CE tab/workspace side effects.

Complexity: 76/100.

Quick commands:
- python3 scripts/run_tests_parallel.py
- cd plugins/flow-next/scripts && bash smoke_test.sh
- ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
- claude plugin validate plugins/flow-next
- live CE smoke through `.flow/bin/flowctl rp` with pre/post `rpce-cli --raw-json -e windows` inventories
- cd ~/work/flow-next.dev && pnpm build
## Acceptance
- [ ] Final report contains reproducible pre/post medians and operation counts for help/usage/setup-mode/config/list/status/specs/prime/export/memory/cascade/pilot.
- [ ] No optimized path regresses >10% without an explicit correctness justification accepted in the evidence.
- [ ] Full parallel suite, focused platform/launcher/locking tests, shell smokes, mirror idempotency, plugin validation, and docs build pass.
- [ ] Python 3.11 and latest-stable gates pass; Windows tests prove real lock behavior.
- [ ] Canonical flowctl, plugin-bin, dogfood copy, Ralph copy, templates, and Codex mirror are synchronized with fn-121 invariants intact.
- [ ] Live CE smoke records CLI/app versions and resolver path, proves CE is selected over co-installed Classic, and exercises every supported `flowctl rp` wrapper successfully.
- [ ] Two live `rp setup-review --create` calls for the same root return the same numeric CE window; pre/post inventories prove no duplicate workspace window was created.
- [ ] CE smoke validates prompt/selection round trips, prompt export content, and a minimal chat transport/session ID; temporary files are removed and intentional CE UI state is documented.
- [ ] Worktree scope is clean apart from intended fn-122 artifacts and associated code/docs changes.
- [ ] Completion evidence lists commits/tests, retained/deferred findings, and confirms no version bump or release.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

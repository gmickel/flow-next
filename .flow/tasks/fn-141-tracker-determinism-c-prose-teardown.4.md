---
satisfies: [R8, R9, R10, R11, R12, R13]
---
# fn-141-tracker-determinism-c-prose-teardown.4 Supersede fn-57 R3; rewrite repo docs

## Description
Record the fn-57 R3 supersession at all three assertion sites so nothing ships contradicting a live criterion: `cmd_sync_check`'s "NO tracker-mutation code lives here or anywhere in flowctl (R3)" docstring, the `list-dep-relations` transport-blind docstring, and `docs/tracker-sync.md:238`'s "flowctl has no tracker transport".

Rewrite `docs/tracker-sync.md` (Transport ladder becomes flowctl-owned; document `tracker.resolved` + capability degradation). Add `## flowctl tracker` to `docs/flowctl.md` modelled on `## flowctl sync`, covering every verb, the result envelope, class enum and numeric exit codes. Correct the Jira apiVersion default to 2.

Update the doc-index rows still using "transport ladder" as user-facing vocabulary (`README.md`, `docs/README.md`, `docs/teams.md`, `CLAUDE.md`), and re-measure `agent_docs/optimizing-skills.md`'s always-loaded weight for tracker-sync.

## Acceptance
- [ ] All three fn-57 R3 assertion sites updated with a pointer to this batch
- [ ] docs/flowctl.md has a complete `## flowctl tracker` section incl. envelope + class enum + exit codes
- [ ] Jira apiVersion default corrected to 2
- [ ] No doc teaches runtime transport-ladder reasoning (all four index rows)
- [ ] optimizing-skills.md weight re-measured

## Done summary
Documented flowctl-owned tracker transport, the complete `flowctl tracker` command and error contract, resolved capabilities and provider degradation, Jira version 2 convergence, and the supersession of fn-57 R3. Removed runtime transport-ladder guidance, refreshed tracker prompt-weight evidence and generated mirrors, and corrected adjacent Jira and GitHub fidelity claims found during review.
## Evidence
- Commits: 03c0c9e16af4e37d6cdd5bc00d6ff12916614747, 0b1bf1e67f643f84a4686b3ae85612b81f79eb21, 8b3a7170a8cdb2b355addee0b2297235a39242e9, 05d42c3375bf45f0c4581712d46d8b4e809e12ad
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q, cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_tracker_sync_backlog_mode test_tracker_resolution_linear_jira -q, cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_tracker_capabilities.GithubSubIssuesHierarchy -q, git diff --check, tracker documentation contract and LF-normalized prompt-weight assertions, GATE_SKIPPED:unittest:green-receipt 05d42c33 - baseline reused from prior post-gate pass
- PRs:
---
satisfies: [R5, R6, R10]
---
# fn-73-glab-git-ops-make-prresolve-prland-over.4 flow --auto ends at the MR on GitLab, plus docs and the live end-to-end run

## Description
Lets `flow --auto` verify the MR make-pr opened and stop there on a non-GitHub forge, keeps goal mode from trying a GitHub PR on GitLab, ships the docs and changelog, and runs make-pr end to end against the live GitLab project.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-flow/auto.md`, `plugins/flow-next/skills/flow-next-flow/references/tail.md`, `plugins/flow-next/skills/flow-next-flow/references/goal-mode.md`, `plugins/flow-next/docs/flowctl.md`, `CHANGELOG.md`, `plugins/flow-next/tests/test_flow_auto.py`
**Touches:** [plugins/flow-next/skills/flow-next-flow/**, plugins/flow-next/docs/**, CHANGELOG.md, plugins/flow-next/tests/test_flow_auto.py, plugins/flow-next/codex/**, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json]

### Approach
- `auto.md` make-pr verify (:443-451): keep the `PR_VERIFY_FAILED` gh fence byte-for-byte (`test_flow_auto.py` executes it). Add: when the snapshot's `forge` is not `github`, verify by re-running `flowctl pilot snapshot --spec <id>` and reading `selected.pr.open`; a failed snapshot or `probe_failed` is the same crash-class `NEEDS_HUMAN`. Make the reason strings forge-neutral where they say "gh probe failed" only if tests allow; otherwise leave them.
- `auto.md` prerequisites (:16, :145): name the forge's CLI rather than `gh` only.
- `tail.md`: one sentence keyed on the snapshot's forge (not on "gitlab"): on a forge other than GitHub, the run stops after make-pr with the PR/MR URL and `NEEDS_HUMAN`, never dispatching land. fn-317 removes it in one line.
- `goal-mode.md:126`: on a forge other than GitHub, the integration-branch PR stops `NEEDS_HUMAN`.
- Docs: `docs/flowctl.md` notes the snapshot `forge` field; CHANGELOG `## Unreleased` entry crediting @janhommels for the measured glab behaviour and @TechupBusiness for #462. Regenerate the Codex mirror and the tracker manifest.
- Live end-to-end (maintainer's GitLab test project): a throwaway spec on a branch of `flownext/flownext`, make-pr opens the MR, `--update` and `--ready` work, `flow --auto` verify reads it and the tail stops. Record what ran and what it showed in the task's done summary; delete the test MR and branch afterwards.
- Run the full suite once at the end (`python3 scripts/run_tests_parallel.py`, `uvx ruff@0.16.0 check .`).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-flow/auto.md:10-20,140-150,440-460` — prerequisites, gh rule, verify fence
- `plugins/flow-next/skills/flow-next-flow/references/tail.md:1-50` — destination and binding
- `plugins/flow-next/tests/test_flow_auto.py:290-330` — the executed verify fence

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-flow/references/goal-mode.md:120-130`
- `agent_docs/adding-skills.md` — shipped-skill rules

### Key context
- fn-268 edits the same tail prose; rebase if it lands first.

## Acceptance
- [ ] On a non-GitHub forge `flow --auto` verifies the MR through the snapshot and stops after make-pr with its URL and `NEEDS_HUMAN`
- [ ] GitHub verify fence unchanged; `test_flow_auto.py` passes unmodified (R10)
- [ ] Goal mode stops `NEEDS_HUMAN` at the integration-branch PR on a non-GitHub forge
- [ ] Docs and CHANGELOG updated; Codex mirror and manifest regenerated
- [ ] Live make-pr end-to-end on the GitLab test project recorded (create, update, ready, verify, tail stop); test MR and branch removed
- [ ] Full suite and ruff pass

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:

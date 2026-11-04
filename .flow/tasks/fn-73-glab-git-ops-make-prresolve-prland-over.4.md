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
`flow --auto` now confirms the merge request make-pr opened on a forge other than GitHub and stops there. On such a forge, auto.md's make-pr verify skips the gh fence: it reruns the snapshot fence, reloads the persisted snapshot, and reads `selected.pr`. A failed probe, a missing row or unparseable output is the crash-class `NEEDS_HUMAN`. tail.md stops the run after make-pr, or at an existing open PR, with the PR URL and `NEEDS_HUMAN`, whether or not landing is authorized, and never offers, defers to or dispatches land. Goal mode stops `NEEDS_HUMAN` before opening its integration-branch PR. The prerequisites and the Forbidden gh rule name the forge's CLI, and the PR probe reasons are now forge-neutral ("PR probe failed at ..."). flowctl.md documents the snapshot's `forge` field. CHANGELOG `## Unreleased` has the entry crediting @janhommels and @TechupBusiness. The Codex mirror is regenerated; the tracker manifest is unchanged because no Python changed.

Tier: session (jev moderate 0.23) at default effort (model: claude-opus-5-5[1m])

Evidence (measured):
- Live end to end in a scratch Flow repo cloned from `flownext/flownext` (repo flowctl, `GITLAB_HOST=localhost:8929`). It used a throwaway spec on branch `fn73-e2e-auto` with one task done. I ran make-pr's sourced preflight, export, aid write and render, then `make-pr-create.sh`.
  - Create, `--draft`: preflight set `FORGE=gitlab` and closed the spec. The run pushed the branch and opened !12 (`Draft: fn73 e2e greeting file`, `draft: true`, target `main`) with the rendered body.
  - `--update`: I first set the description to a stale text. The update found MR 12, replaced the description with the rendered body, and kept the draft.
  - `--update --ready`: the title lost `Draft: ` (`draft: false`, still `opened`).
  - Verify: I took auto.md's snapshot fence and the new verify fence from the repo file and ran them in the clone. They gave `forge: gitlab`, route `existing_pr_tail`, `probe_failed: false`, and `OPEN_PR_URL=http://localhost:8929/flownext/flownext/-/merge_requests/12` with `PR_VERIFY_FAILED=0`. That route on a non-GitHub forge is tail.md's stop, `NEEDS_HUMAN` with the URL.
  - Failing glab: with a glab shim that fails API reads, the same fences gave `probe_failed: true` and `PR_VERIFY_FAILED=1`.
  - Cleanup: MR !12 and branch `fn73-e2e-auto` were deleted through the API. The project is back to MRs !1-!7 and its fixture branches.
- Tests: one new table-driven test in `test_flow_auto.py` (`test_make_pr_verify_off_github_reads_the_snapshot`) runs the off-GitHub fence in a fresh shell with `PILOT_SNAPSHOT` unset. It checks the open URL, no open row, `probe_failed`, a missing `selected` and malformed JSON. The existing tests, including the GitHub verify-fence tests, are unmodified and pass. The gh fence is byte-for-byte unchanged (R10).
- Focused Quick commands (test_forge, judge_route, pilot_snapshot, make_pr_preflight_auth, make_pr_close, flow_auto) passed, 78 tests. `sync-codex.sh --check` passed.
- Full suite (`python3 scripts/run_tests_parallel.py`, log `.flow/tmp/fn73.4-full-suite.log`): 4160 ran, 1 failure, inherited and not caused by this task. `test_tracker_package_import.py` flags `test_forge.py` (added by task .1, unchanged here), because its `sys.path.insert(0, str(SCRIPTS))` does not contain the lowercase word `scripts` the static check looks for. The fix is one line in `test_forge.py` (for example `sys.path.insert(0, str(TESTS.parent / "scripts"))`). That file is outside this task's Touches, so I did not edit it.
- `uvx ruff@0.16.0 check .` passed.
- Baseline: green (77 focused tests, with `PYTHONPATH=plugins/flow-next/tests`, pre-existing).

Decisions:
- The non-GitHub stop is keyed on the snapshot's `forge` being set and not `github`. An unknown origin (`forge: null`) keeps today's GitHub-adapter behaviour, as R4 says for the readers.
- On a non-GitHub forge the tail stops `NEEDS_HUMAN` even without landing authority, instead of `DEFERRED_TO_LAND`, because land cannot run there yet. auto.md's OPEN-PR bullet points at that stop first.
- The verify reuses the existing snapshot fence instead of adding a second snapshot call shape.

Review: codex, one reviewer (correctness). NEEDS_WORK on one P1: the new fence read `$PILOT_SNAPSHOT` without reloading the persisted file, so a verify run in its own tool call reported a false probe failure. Fixed in 23f63ea79, with the test changed to run in a fresh shell. The re-review returned SHIP. Memory entry captured: `bug/runtime-errors/skill-fence-read-a-shell-variable-an-2026-11-04`.

Follow-ups:
- `test_forge.py`'s scripts-path insert (above) keeps the full suite red until it is changed.
- The rendered briefing's "Start at" link is `/<project>/blob/<sha>/<path>`, GitHub's form. GitLab's route is `/<project>/-/blob/<sha>/<path>`. I could not confirm whether GitLab redirects the legacy form, because the test project is private and the check needs a browser session. Not verified.

stage: impl-review - ran [2026-11-04..2026-11-04]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 52c6d33ee42a7a31fa611ab4346090683dd86885, 23f63ea7948853cebe890884407418003111de5d, 9d7cf647a6a4439f0aae5909b360608b0428dbf9
- Tests: python3 -m unittest (focused Quick commands, PYTHONPATH=plugins/flow-next/tests): 78 OK, python3 scripts/run_tests_parallel.py: 4160 ran, 1 inherited failure (test_tracker_package_import flags test_forge.py from task .1), uvx ruff@0.16.0 check .: pass, live GitLab make-pr create/update/ready + auto.md verify fence: pass
- PRs:
---
satisfies: [R8, R9, R10, R11]
---
# fn-145-opus-5-autonomous-seam-retune.4 Regenerate, verify, land, and update downstream docs

## Description
Regenerate cross-platform artifacts, record the retune, run the complete gate,
and prepare the spec-derived branch for completion review and PR creation.
Landing, the public docs-site update, and the concurrent-branch coordination
prompt are immediate post-task lifecycle actions because their evidence exists
only after this task and the completion-review gate are done.

**Size:** M

**Files:**
- `plugins/flow-next/codex/`
- `CHANGELOG.md`
- `agent_docs/optimization-log.md` when measured evidence exists
- downstream `/Users/gordon/work/flow-next.dev` Work/autonomy documentation

### Approach

- Regenerate the Codex mirror twice and inspect the introduced mirror diff.
- Add an Unreleased changelog note; no plugin version bump.
- Run focused suites, full parallel tests, pinned Ruff, and relevant smoke
  checks before PR creation.
- Leave a precise downstream file/build handoff for flow-next.dev.
- After this task reaches done, the conductor runs completion review,
  spec-derived make-pr, the normal bounded land procedure, then applies and
  verifies the downstream update.
- Only after merge, produce a self-contained prompt naming the actual main
  commit, overlapping paths, gates, and inspect-before-rebase guidance.

### Investigation targets

**Required:**
- `scripts/sync-codex.sh`
- `CHANGELOG.md`
- `agent_docs/optimization-log.md`
- `agent_docs/releasing.md`
- `/Users/gordon/work/flow-next.dev/AGENTS.md` or project instructions
- `/Users/gordon/work/flow-next.dev/src/content/docs/skills/work.mdx`
- `/Users/gordon/work/flow-next.dev/src/content/docs/autonomous/overview.mdx`

**Optional:**
- `/Users/gordon/work/flow-next.dev/src/content/docs/skills/pilot.mdx`
- `/Users/gordon/work/flow-next.dev/src/content/docs/review/workflow.mdx`

### Key context

The docs site is a separate repository and must follow its own clean-worktree,
branch, test, PR, and landing rules. Neither its landing evidence nor the
coordination prompt can exist before the main PR merge; they are spec-run
follow-ups, not preconditions for marking this implementation task done.
## Acceptance
- [ ] Canonical changes and generated Codex mirror are aligned; two consecutive
  sync runs are clean/idempotent.
- [ ] Repo Unreleased changelog records the behavior change without a version
  bump; optimization log records only measured evidence.
- [ ] Focused suites, full parallel tests, Ruff 0.16.0, and relevant smokes pass.
- [ ] Branch is clean and ready for the mandatory completion review and
  spec-derived make-pr workflow.
- [ ] Exact flow-next.dev files, copy, and documented verification command are
  captured for the post-main-merge downstream update.
- [ ] Post-task handoff explicitly requires normal landing, downstream
  verification/landing, and a final concurrent-agent prompt using the actual
  main merge commit and overlap set.
## Done summary
Implemented the fn-145 integration closeout: regenerated the Codex mirror twice with an identical tree hash (`6d3353d49d729ffa0e9e645394beab67e996b84628cf8d39a57b4cf091d3b6ce`), refreshed measured Plan Review reached-path evidence, added the Unreleased changelog entry, and recorded the measured Work/Pilot/Plan Review reached paths. The pre-edit full-suite baseline exposed one inherited-but-in-scope stale evidence assertion (2,779/2,780 passed); refreshing that artifact brought the focused suite and full suite green.

Commit: `4dba4816eac798acb9e6da34d1f2e05357f48aba`

Verification:

- `cd plugins/flow-next/tests && python3 -m unittest -q test_codex_delegation_gates test_skill_prose_diet test_work_reached_path_routes test_host_review_backend test_pilot_backlog_mirror_safety test_prompt_text_pinned` — 106 passed.
- `./scripts/sync-codex.sh` twice — both passed; generated mirror hash identical after each pass.
- `python3 scripts/run_tests_parallel.py` — 2,780 passed, 0 failures, 0 errors, 4 skipped.
- `uvx ruff@0.16.0 check .` — `uvx` unavailable in this environment; the repository CI-compatible exact-version fallback (`ruff==0.16.0` in `/tmp/fn145-t4-ruff-venv`) passed with `All checks passed!`.
- `git diff --check` passed; worktree clean after commit.

Host-deferred terminal state:

- Leave `fn-145-opus-5-autonomous-seam-retune.4` `in_progress`.
- Host runs the mandatory review against base `6f547b9800e35228c14260ee591ab9c88c6cbbbd`, then calls `flowctl done` only on SHIP.
- Normal spec completion review, PR creation, and `/flow-next:land` remain required; do not treat this worker commit as a main-branch landing.

Exact post-main-merge flow-next.dev handoff (not performed here):

1. In `/Users/gordon/work/flow-next.dev/src/content/docs/skills/work.mdx`, replace the current one-time-consent bullet with:

   > **One-time sandbox consent** — an interactive first delegated run asks once and persists the choice: **yolo** (default; full access including network) or **full-auto** (`workspace-write`, tighter blast radius, no network). Headless/autonomous Work — `FLOW_RALPH=1`, a nonempty `REVIEW_RECEIPT_PATH`, `FLOW_AUTONOMOUS=1`, or parsed `mode:autonomous` — never opens that prompt. With no persisted consent, delegation stays off and Work continues through the standard in-session implementation path without writing consent; pre-granted consent permits delegation.

2. In the same file, replace the current “Ralph and attribution” paragraph with:

   > Delegation runs in interactive and autonomous modes. Ralph, review-receipt, `FLOW_AUTONOMOUS=1`, and parsed `mode:autonomous` invocations all use the same no-question rule: pre-granted consent may delegate; missing consent disables delegation for that run and standard Work continues. A `ralph-guard` hook allowlists the exact canonical Ralph invocation. Commits retain mixed-model attribution, so code Codex wrote remains recorded as Codex's.

3. In `/Users/gordon/work/flow-next.dev/src/content/docs/autonomous/overview.mdx`, add this bullet under “Unattended runs”:

   > **Delegation consent never stalls a tick**: `FLOW_RALPH=1`, a nonempty review-receipt path, `FLOW_AUTONOMOUS=1`, and parsed `mode:autonomous` suppress delegation questions. If consent was not persisted beforehand, Codex delegation stays off and Work continues in-session; the loop does not write a synthetic consent decision or stop for input.

4. In the same file, replace the “Same review gates” safety bullet with:

   > **Same review gates** — plan-review, impl-review, and spec-completion-review fire exactly as they do interactively; autonomy suppresses *questions*, never *gates*. Only the selected backend's mechanics load — host-native subagent machinery remains cold unless `host` is selected — and a selected backend continues through its shared fix/status path in the same invocation.

5. Verify exactly:

   `cd /Users/gordon/work/flow-next.dev && pnpm build`

6. Commit/push the downstream docs only after the flow-next change is actually on `main`, citing that main SHA in the downstream commit/PR.

Final concurrent-agent prompt after the actual main merge:

> Verify fn-145 closure in parallel. Agent A: confirm the landed flow-next main SHA contains all fn-145 commits, task/spec terminal states and receipts, and green CI/full-suite/Ruff evidence. Agent B: apply the exact flow-next.dev handoff to `src/content/docs/skills/work.mdx` and `src/content/docs/autonomous/overview.mdx`, run `pnpm build`, and return the downstream commit SHA and clean status. Agent C: independently diff canonical vs Codex mirror for the touched seams and audit public-doc behavior parity. Join all results; report complete only with the flow-next main SHA, downstream SHA, build/test evidence, and no uncommitted changes.
## Evidence
- Commits: 4dba4816eac798acb9e6da34d1f2e05357f48aba
- Tests: baseline: red (python3 scripts/run_tests_parallel.py failed pre-edit: stale tracked plan-review reached-path evidence; 2779/2780 passed), cd plugins/flow-next/tests && python3 -m unittest -q test_codex_delegation_gates test_skill_prose_diet test_work_reached_path_routes test_host_review_backend test_pilot_backlog_mirror_safety test_prompt_text_pinned (106 passed), ./scripts/sync-codex.sh (twice; generated mirror hash 6d3353d49d729ffa0e9e645394beab67e996b84628cf8d39a57b4cf091d3b6ce remained identical), python3 scripts/run_tests_parallel.py (2780 passed, 0 failures, 0 errors, 4 skipped), uvx ruff@0.16.0 check . (uvx unavailable; exact ruff 0.16.0 CI-compatible pip fallback passed), git diff --check
- PRs:
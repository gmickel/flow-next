# 9.11.0 pre-release fixes for issue start, intake and tracker linking

## Goal & Context

fn-324 (#606), fn-325 (#608) and fn-314 (#607) merged on 2026-11-15 and are unreleased. A pre-release audit (Codex gpt-6.1-sol, three lenses over b66dfb5ac..877858005, all NEEDS_WORK) plus the live recordings and end-to-end runs found defects that must be fixed before 9.11.0 ships. Gordon's rule: flow-next never releases broken or untested work. [user]

Two of the defects let an unattended `flow --auto --from-issue` run build the wrong thing or skip a gate it promises (interrupted capture skipping review and push; a Jira URL from another site). Gordon decided on 2026-11-15 that an issue start always runs implementation review. [user]

## Architecture & Data Models

- **Issue start (fn-325)** lives in prose: `skills/flow-next-flow/references/issue-start.md`, `skills/flow-next-capture/references/from-issue.md`, and `auto.md`'s gate. Fixes stay in that prose unless a deterministic fact needs flowctl (the burden-of-proof rule: two consumers, or zero judgment). [inferred]
- **Spec identity across refs:** resolve-before-capture must see a tracker link wherever a fetched ref's spec JSON carries it, including specs already on the default branch and JSON-only changes. Today it reads only `specs --refs` `summary.branch_only`, whose live set is body-based. [inferred]
- **Question rounds:** `tracker wire question` dedupes by a stable id (subject, stage, reason, slug) and reopens a round only on a `flow-next:answer` marker. Issue start treats a plain reply plus a board return as the answer. The two must agree so a follow-up question is posted, not silently deduped. [inferred]
- **Capture merge-base seeding (fn-324):** the tracker half must be stored as `trackerBodyForMerge(issue_body)` (what push compares against), the flow half as the source body. [inferred]
- **Linear `list-open`:** selects labels only for compact requests (`--any-lane`/`--unlinked`); the default query and rows stay as 9.10.0. [inferred]

## API Contracts

- No new flowctl verb unless resolve-across-refs needs one; if added, it is read-only, has `--json`, and appears in flowctl-help.txt with HELP_SHA256 regenerated under python3.14. [inferred]
- `glab api ... --hostname <host[:port]>`: a self-managed GitLab host on a non-default port keeps its port. [inferred]

## Edge Cases & Constraints

- **Interrupted capture:** a run killed after `spec ready` and before the capture commit (or after the commit, before the push) must, on re-entry, finish commit, push and design review before any work hop, or stop `NEEDS_HUMAN`. It must never reach work as an ordinary linked spec. [inferred]
- **Jira URL from another site:** a `--from-issue` URL whose host is not the configured Jira base stops before any write. A bare key still works. [inferred]
- **Plain answer, then a follow-up question:** posted as a new round; a crash-and-rerun of the same round still does not double-post. [inferred]
- **Issue start and review:** every work hop of an issue start runs implementation review on the configured backend; the working-rules risk-rule skip does not apply. No backend configured keeps the existing skip with its note. [user]
- **Capture push status:** an issue start's capture push must not report a backlog-vs-ready status conflict for an issue that is in the ready lane by consent. [inferred]
- **`--auto` after a merge:** the checkout is left on the merged, remote-deleted spec branch with a sync-state file changed. Establish whether the next `--auto` run misroutes from that state; fix it if it does, else record why it is harmless. [inferred]
- **install-codex.sh** must not delete files outside the Codex home when `CODEX_HOME` contains spaces or other characters xargs splits. [inferred]

## Acceptance Criteria

- **R1:** An issue start interrupted between `spec ready` and its capture push completes commit, push and design review on re-entry before any work hop, or stops `NEEDS_HUMAN`; never reaches work as an ordinary linked spec. A prose-contract test pins the recovery rule. [inferred]
- **R2:** Resolve-before-capture finds a spec linked to the issue on any fetched ref, including a spec present on the default branch whose link exists only on a remote branch and a JSON-only link change; a test covers the remote JSON-only case. [inferred]
- **R3:** After a refused issue gets a plain reply and returns to the ready lane, a follow-up question on the same topic is posted as a new round (not deduped against the old one), and rerunning the same round does not double-post. Test: refusal → plain reply → re-promotion → follow-up posts once. [inferred]
- **R4:** A `--from-issue` Jira URL whose site differs from the configured base stops before any write; a bare key and a same-site URL work. [inferred]
- **R5:** Every work hop of an issue start runs implementation review on the configured backend; the risk rule never skips it there. A prose-contract test pins it. [user]
- **R6:** An issue start's capture push reports no status conflict for an issue in the ready lane; recorded live on Linear. [inferred]
- **R7:** Capture's named-issue merge-base seed stores the tracker half as `trackerBodyForMerge(issue body)`; the first push of an unchanged issue whose body ends in a newline or carries a `flow:deps` region does not return `tracker_diverged`. Test through the prescribed seeding path. [inferred]
- **R8:** Linear `list-open` without flags returns the same query and rows as 9.10.0; labels are selected only for `--any-lane`/`--unlinked`. A test compares the default query against a fixed baseline. [inferred]
- **R9:** `install-codex.sh` with a `CODEX_HOME` containing a space deletes nothing outside that home; `test_codex_config_merge` passes when run from `plugins/flow-next`. [inferred]
- **R10:** With `tracker.perTracker.host` set to `http://localhost:8929`, `tracker resolve` and `list-open` reach the self-managed GitLab instance; recorded live. [inferred]
- **R11:** The `--auto` post-merge checkout state is either fixed so the next `--auto` run starts cleanly, or shown harmless by a recorded next run; the finding states which. [inferred]
- **R12:** Before release, a headless `flow --auto --from-issue <key> --until=merge` run on the final code passes on gmickel/flow-next-e2e-scratch for a clear issue (implementation review runs) and for refused → plain answer → follow-up question → answer → build. [user]
- **R13:** After make-pr's tracker call, a change it wrote to the spec's JSON (sync state, or the link it created for an unlinked spec) is committed alone and pushed to the pull request branch, so it reaches the PR and the default branch; a failed push warns and leaves the PR as it is. Found by task 4. [inferred]

## Boundaries

- No new skill, command or config key. [inferred]
- No change to the working-rules risk rule outside issue starts. [user]
- No Jira Data Center live recording (no instance); its classic-search path stays fake-transport covered. [inferred]
- No version bump or release inside this spec; the release follows it. [user]

## Decision Context

- **Always review an issue start** (Gordon, 2026-11-15): nobody wrote the spec and nobody reads the code before an unattended merge, so the risk rule's small-change skip does not hold there. [user]
- **Linear labels:** fn-314's review fix selected labels for default rows too; R4 of fn-314 promises unchanged default output, so labels move behind the compact flags. [inferred]
- **One spec, several tasks by file ownership:** the defects span the issue-start prose, the tracker package and the installer; separate owners let workers run in parallel without conflicts. [inferred]

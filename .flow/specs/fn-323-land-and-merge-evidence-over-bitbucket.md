# land and merge evidence over Bitbucket pull requests

> **Captured 2026-11-13** from GitHub issue #602 (filed by @benjamin-benz-42, who tests and contributes). Third of three Bitbucket specs: the Bitbucket Cloud forge adapter and make-pr, resolve-pr over Bitbucket PR comments, then this one. Completes the idea → merged-PR loop on Bitbucket Cloud, as fn-317 did on GitLab.

## Goal & Context
<!-- Source: 70% [paraphrase] / 30% [inferred] -->

With make-pr and resolve-pr working on Bitbucket, the last manual step is merging: `/flow-next:land` merges through `gh` or GitLab's merge API, and the tracker accepts only a merged GitHub PR or GitLab MR as evidence for Done. A Jira-tracked spec on a Bitbucket repository therefore never reaches terminal Done. This spec lets land merge a Bitbucket PR under the same safety rules, lets `flow --auto --until=merge` finish on a Bitbucket origin, and makes a merged Bitbucket PR count as merge evidence.

## Architecture & Data Models

- **A readiness read in the adapter.** Whether a PR is ready to merge is a deterministic, safety-critical decision, so it is an adapter read, not per-forge prose, reaching land through `flowctl pilot snapshot` as on GitLab. It covers the build statuses reported on the current head commit, the participants' approvals and requested changes, whether Bitbucket would accept the merge, the head SHA, and whether squash is allowed. [paraphrase]
- **A merge-evidence read in the adapter.** A merged PR, its real merge time and its changed paths (old and new) answer the tracker's "never terminal without merge evidence" rule through the same interface. [paraphrase]
- **Merging is an action.** The merge stays with the agent in land's `forge-bitbucket.md`, loaded by forge name. GitHub and GitLab skill paths are not edited. [paraphrase]

## API Contracts

- Record live before relying: build statuses on a PR's head commit, participants' approval and requested-changes states (with a second workspace user), Bitbucket's own merge-blocking answer, the merge call with the squash strategy and whether it can be bound to an expected head, the merged PR's merge commit and merge time, and its changed paths. [inferred]

## Edge Cases & Constraints

- Build states other than success (in progress, failed, stopped, none reported) count as not green. Anything unreadable counts as not green. [inferred]
- A participant with requested changes blocks readiness. An unreadable approval state counts as not approved. [paraphrase]
- A repository whose settings forbid the squash strategy makes land stop with `NEEDS_HUMAN`; it never picks another merge strategy. [inferred]
- GitHub-only land steps (merge queue, rulesets, `update-branch`, rerunning failed checks) have no Bitbucket arm here; where land needs one on Bitbucket, it stops with `NEEDS_HUMAN`. [inferred]
- Never auto-merge. [inferred]
- A fork's PR, or a PR without a spec, has no readiness read, and land stops `NEEDS_HUMAN` on it, as on GitLab. [inferred]

## Acceptance Criteria

- **R1:** The Bitbucket adapter returns a normalized readiness state (head SHA, build state on that head, approval state, Bitbucket's merge-blocking answer, squash allowed, ready); unreadable build or approval states read as not green and not approved, and a participant with requested changes reads as not approved. [paraphrase] Errors: any failed read returns the not-ready state, never a partial ready.
- **R2:** On a Bitbucket origin, land merges only when ready, squashes, never enables auto-merge, never merges a head other than the one it judged ready, and reports `MERGED` with the merge commit. [inferred] Errors: a head that moved between the readiness read and the merge does not merge (see Parked unknowns for how); a failed merge call is reported with Bitbucket's answer.
- **R3:** A repository that forbids squash, or a land step with no Bitbucket arm, stops land with `NEEDS_HUMAN`. [inferred] Errors: no error surface beyond the stop message naming the reason.
- **R4:** A merged Bitbucket PR is merge evidence for tracker Done, read through the adapter with its real merge time and changed paths, under the same "never terminal without merge evidence" rule as a merged PR or MR. [paraphrase] Errors: a failed or truncated read is `probe-error`, never a false Done.
- **R5:** `flow --auto --until=merge` on a Bitbucket origin dispatches land on the PR, replacing the first spec's stop after make-pr. [inferred] Errors: no error surface beyond land's own verdicts.
- **R6:** Behaviour on GitHub and GitLab origins is unchanged; the existing land and merge-evidence tests pass unmodified. [inferred] Errors: none.
- **R7:** Each `bkt` command this spec relies on is first run against the live Bitbucket Cloud test workspace (with a second user for approval and requested-changes states) and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1–R5 in CI. [paraphrase] Errors: none beyond the fixtures being real output.

## Boundaries

- No new public flowctl verb and no config key. [paraphrase]
- No auto-merge and no merge queue equivalent. [inferred]
- Spec approval through PR reviews (`spec.approval pr`) stays GitHub-only, as on GitLab; Bitbucket approvals feed readiness only. [inferred]
- Bitbucket Cloud only; no Data Center. [paraphrase]

## Parked unknowns

- **Head binding on merge (answered 2026-11-13, measured).** Bitbucket Cloud's merge call cannot be bound to an expected head: sent a `sha` with the head it was judged at, it ignored it and squash-merged the branch's moved head, and the merged pull request then reports that moved head as its source commit. R2 is met as narrowly as Bitbucket allows: land reads the pull request and its readiness again immediately before the merge call and merges only when both still name the judged head, then compares the merged pull request's source commit with that head and, when they differ, reports the merge with both heads named so a person checks the commits between them. [inferred]
- Beside a `q` query, Bitbucket ignores the `state` parameters and lists every state (measured 2026-11-13: a declined pull request came back under `state=OPEN`). An open-only read puts the state inside `q` (`state="OPEN" AND ...`), and rows are checked for their state; this also corrects resolve-pr's current-branch lookup from fn-322. [inferred]
- On the free plan Bitbucket did not block the merge of a pull request whose build was `STOPPED` (measured 2026-11-13); land's readiness gate, not Bitbucket's, is what holds a merge back. [inferred]

## Strategy Alignment

- **Cross-platform parity** — completes the idea → merged-PR loop on Bitbucket Cloud. [strategy:Cross-platform parity]
- **Autonomous mode** — `flow --auto --until=merge` reaches a merge on a Bitbucket origin under the same consent rule. [strategy:Autonomous mode]

## Decision Context

### Motivation
Merging is the last manual step for Bitbucket teams once make-pr and resolve-pr work, and Jira-tracked specs on Bitbucket need a merged PR as evidence for Done. The full live end-to-end run (idea → merged PR) happens once this spec lands; the issue author offered to test on a real Bitbucket Cloud + Jira setup.

### Implementation Tradeoffs
- **Readiness and merge evidence as adapter reads, merging as an action**, exactly as fn-317 decided for GitLab. [paraphrase]
- **Merge time from the merge, not `updated_on`.** Bitbucket's `updated_on` moves with every later comment, so it cannot date a merge. [paraphrase]
- **Spec approval left out.** The issue proposed approval rows for Bitbucket; GitLab ships without them and no Bitbucket user has asked for PR-review spec approval yet, so it can follow on request. [inferred]

# land and merge evidence over GitLab merge requests

> **Split from fn-73 on 2026-11-04** (GitHub issue #462). Third of three GitLab specs: fn-73 (forge adapters and make-pr), resolve-pr over MR discussions, then this one. Completes the idea → merged-MR loop on GitLab.

## Goal & Context
<!-- scope: business -->

With make-pr and resolve-pr working on GitLab, the last manual step is merging: `/flow-next:land` reads GitHub checks and merges with `gh`, and the tracker only accepts a merged GitHub PR as evidence for Done. This spec lets land merge a GitLab MR under the same safety rules, lets `flow --auto --until=merge` finish on a GitLab origin, and makes a merged MR count as merge evidence.

## Architecture & Data Models
<!-- scope: technical -->

- **A readiness read in the adapter.** Whether an MR is ready to merge is a deterministic decision that land's safety depends on, so it is a flowctl read, not per-forge prose: the GitLab adapter (fn-73's interface) returns one normalized state covering pipeline status, approval state and the head SHA. land's GitLab reference reads it. land's GitHub path keeps its current reads, so the GitHub adapter does not implement this read in this spec.
- **A merge-evidence read in the adapter.** A merged MR (and its changed files) answers the tracker's "never terminal without merge evidence" rule through the same adapter interface.
- **Merging is an action.** The merge itself stays with the agent in land's `forge-gitlab.md`, loaded by forge name. GitHub skill paths are not edited.

## API Contracts
<!-- scope: technical -->

- Record live before relying: MR pipeline status, MR approval state (including when the tier hides it), the merge call with the expected head SHA (the merge API's `sha` parameter) and squash, and the merged MR's merge commit and changed files.
- `glab mr merge` may enable auto-merge by default in recent versions; this is unverified. If it does, land uses the API call instead.

## Edge Cases & Constraints
<!-- scope: technical -->

- GitLab pipeline states are wider than GitHub checks (manual, skipped, canceled, none). Anything land cannot read counts as not green.
- Approvals can be optional, required or unreadable (the tier or permissions hide them). An unknown approval state counts as not approved.
- A project that forbids squash merges makes land stop with `NEEDS_HUMAN`. It never picks another merge method.
- GitHub-only land steps (merge queue, rulesets, `update-branch`, rerunning failed checks) have no GitLab arm here. Where land needs one of them on GitLab, it stops with `NEEDS_HUMAN`.
- Never auto-merge, and no merge trains or merge-when-pipeline-succeeds.
- Token scope: merging needs `api` scope.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The GitLab adapter returns a normalized readiness state (pipeline green or not, approval state, head SHA); unreadable pipeline or approval states read as not green and not approved. [inferred]
- **R2:** On a GitLab origin, land merges only when ready, sends the expected head SHA so a moved head fails the merge, squashes, never enables auto-merge, and reports `MERGED` with the merge commit. [inferred]
- **R3:** A project that forbids squash, or a step with no GitLab arm, stops land with `NEEDS_HUMAN`. [inferred]
- **R4:** A merged MR is merge evidence for tracker Done, under the same "never terminal without merge evidence" rule as a merged PR, read through the adapter. [inferred]
- **R5:** `flow --auto --until=merge` on a GitLab origin dispatches land on the MR, replacing fn-73's stop after make-pr. [inferred]
- **R6:** Behaviour on a GitHub origin is unchanged; the existing land and merge-evidence tests pass unmodified. [inferred]
- **R7:** Each `glab` command this spec relies on is first run against a live GitLab project (on both an Ultimate trial and the Free tier, for the approval states) and its real output saved as a test fixture; tests with a stubbed `glab` built from those fixtures cover R1–R5 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- No new public flowctl verb and no config key.
- No merge trains, merge-when-pipeline-succeeds or auto-merge.
- No Bitbucket, Gitea or other forges.

## Decision Context
<!-- scope: both -->

### Motivation
Merging is the last manual step for GitLab teams once make-pr and resolve-pr work. The full live end-to-end run (idea → merged MR) happens once this spec lands; the reporter of #462 offered to test a branch.

### Implementation Tradeoffs
- **Readiness as an adapter read.** Pipeline and approval classification is deterministic and safety-critical; written as prose per forge it would be duplicated and churn. As a tested read it is written once per forge, and the agent still performs the merge.
- **GitHub's land path is not moved onto the readiness read here.** Its reads are proven; moving them is a separate change with its own evidence.
- **Readiness reaches land through `flowctl pilot snapshot` (decided 2026-11-05 during work).** The adapter's readiness read rides on the snapshot's open merge request for the selected spec, the read flow already takes on every hop, so there is no new verb. A merge request without a spec has no readiness read, and land stops `NEEDS_HUMAN` on it; so do a fork's merge request (the snapshot does not list forks) and one whose spec's `branch_name` names another branch. A selector keyed on the merge request was declined to keep flowctl's surface unchanged; fork merge requests can get one later if GitLab users ask.
- **Approval comes from GitLab's own merge check.** `detailed_merge_status` reports a missing approval on every tier (`not_approved` under a rule that needs one), so the approvals endpoint is not read. GitLab reports one blocking check at a time: any status other than `mergeable` or an approval status leaves approval `unknown`. Free-tier evidence is the merge request reads recorded before the trial; Ultimate evidence is a merge request rule needing a second user, read before and after that user approved.
- **The merge goes through the merge API, never `glab mr merge`.** Whether `glab mr merge` turns on auto-merge stays unverified because land does not use it; the API call with `sha` and `squash` was recorded, and a moved head answers HTTP 409.
- **The tracker reaches the adapter through a hook flowctl sets.** The tracker package never imports flowctl. When flowctl imports the tracker's status or sync modules, it points merge evidence at the forge adapter. When the hook is unset, merge evidence reads through `gh` as before, so a GitLab origin reads `probe-error`, never a false Done.

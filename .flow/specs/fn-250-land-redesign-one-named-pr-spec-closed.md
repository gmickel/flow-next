# Land redesign: one named PR, spec closed at the PR head

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 30% [user], 20% [paraphrase], 50% [inferred] -->

Land is causing problems for the people who use it and for downstream tools that drive it. In essence, all it needs to do is run resolve-pr and merge. Today the skill is about 1,740 lines of prose and shell that an agent re-executes on every tick: repo-wide discovery, a two-signal authorship probe, a ledger, a tick claim with a PID reaper, a post-merge tail with rollback and re-entry, a leased force-push cascade for chains, and a review-signal gate built from bot comment text. Thirteen issues were filed against it between 2026-07-30 and 2026-09-18, most of them defects in that machinery and not in the merge decision.

Land reached that size because it compensates for two design choices elsewhere in flow-next.

1. The record of finished work is never committed. A task's done status lives only in per-clone runtime state. The committed task file reads todo at the branch head, including for merged and closed specs. From a pull request, from the base branch, or from another clone, nothing can tell that the work is complete. Discovery, the authorship probe, the footer marker and the ledger exist to work around this. Since the direct route became the default, the implicit task is minted on the spec branch, so a land tick started from the base branch finds no candidates at all.
2. The spec closes after the merge. Closing then needs a push to the base, which a protected base refuses permanently. The post-merge tail, its rollback, its re-entry path and the open report about a tail failure that no later tick can find all follow from this.

This spec fixes the two design choices and rewrites land as a short prose skill over one named pull request. The goal is a simpler flow-next that can do as much as before for the people who land pull requests with it.

## Architecture & Data Models
<!-- scope: technical -->

- Closing a spec writes each task's final status into the committed task files. Per-clone runtime state goes back to being scratch state while work runs; where it exists it still wins, and where it is absent the committed status answers. [inferred]
- make-pr closes the spec as the last commit on the pull-request branch, before it opens the pull request, so the close does not move the head after review. The squash merge carries the close to the base. The base reads closed exactly when the work merges, and an abandoned pull request never closes anything on the base. GitHub performs the write, so it works on a protected base, from any clone and any checkout. [inferred]
- Spec status follows the tasks: creating or starting a task on a closed spec sets the spec back to open. There is no reopen verb. When the follow-up task finishes, the spec is closed again by make-pr or by whoever lands it. [inferred]
- A pull request ships every spec whose branch name, read at the pull request's head, equals the pull request's head branch. Every head contains every spec file in the repository, so the branch name is what ties a spec to a pull request. One branch may carry more than one spec, and a chain child's head also holds its parent's spec, under the parent's branch name. [paraphrase]
- A closed spec at the pull-request head is proof the work finished, because closing refuses while any task is incomplete. One read of the matching specs at the head replaces discovery, the authorship marker and the all-tasks-done gate. [inferred]
- Land takes one pull request and the current merge authorization. It keeps no files of its own: no ledger, no claim, no list of pending branch deletions. [inferred]
- The review signal is GitHub's own state: checks, review decision, and zero unresolved review threads. [inferred]
- Dependent pull requests rely on GitHub's native stacks. Land links open children into a stack before merging the parent and merges stack layers lowest first through the asynchronous merge call that stacks require. [inferred]

## API Contracts
<!-- scope: technical -->

- Land's input is a pull request. The specs it ships are read from the pull request's head by branch name, never looked up locally first. [paraphrase]
- The terminal line keeps its grammar: `LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<url|-> reason="<one line>"`. The verdict vocabulary is unchanged so existing parsers keep working; `RELEASED` stays in the grammar and is no longer emitted. [inferred]
- Retained config keys: `land.mergeVerdictCommand` and `land.patienceMinutes`. Every other `land.*` key is retired. [inferred]
- The tracker touchpoint on a confirmed merge stays, when the bridge is configured. It is an API call and writes no commit. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- The tracker projection reaches its terminal state only from merge evidence, so a spec that is closed on its branch while the pull request is open still projects as in review. [inferred]
- make-pr also opens pull requests that do not finish a spec (a gate pull request, spec text only). Those specs have incomplete tasks, stay open, and are not landable by land. [inferred]
- A squash merge of a plain chain's parent with branch deletion closes the child pull request, and the ordinary catch-up call cannot resolve a child that edits its parent's lines. Both were reproduced on GitHub on 2026-09-20. A native stack handled the same edits cleanly. [inferred]
- GitHub stacks are a public preview and may change. Without them, or on another forge, a chain whose child conflicts after the parent merges is reported as needing a rebase and land stops. Single pull requests, the large majority, are unaffected. [inferred]
- The head pin needs the full head SHA; a shortened SHA is rejected. [inferred]
- On a native stack the ordinary merge call is refused, and the asynchronous merge call never deletes a branch. A scratch run on 2026-09-20 showed that once the bottom layer's merge is confirmed GitHub has already retargeted and rebased the child, and deleting the merged branch then leaves the child open and clean. Deleting a parent branch while a child still targets it closes the child pull request, which is why the rule in R7 stays in the prose. [paraphrase]
- On a repository with no required reviews where no reviewer ever posted, land merges once the other gates pass. Every merge is explicitly requested, and implementation review ran before the pull request. A repository that needs more states it in its instruction file, enforces it with branch protection, or uses the merge-verdict command. [paraphrase]
- Retired config keys may still be present in existing config files. Reading them must not fail. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Closing a spec writes every task's final status into the committed task files, and in a fresh clone with no runtime state the spec listing, the spec view, validation and the cognitive-aid export all read those tasks as done. Errors: closing still refuses while any task is incomplete and changes no file; where runtime state exists for a task it still takes precedence. [inferred]
- **R2:** When every task of the spec is done, make-pr closes the spec as the last commit on the branch before it opens the pull request, and the pull request's head carries the closed spec. Before the close commit make-pr makes sure the spec's branch name equals the pull request's head branch, setting it when it is absent or different. The close commit exists before make-pr composes the aid artifact, which is bound to the head, so the artifact is not stale at birth. Errors: with an incomplete task, make-pr opens the pull request without closing and says so; a dry run closes nothing; a failed close stops make-pr before the pull request is opened and reports the reason. [inferred]
- **R3:** Creating or starting a task on a closed spec sets the spec back to open, and the spec stays open until it is closed again. Errors: completing the follow-up task does not close the spec by itself; a closed spec with no task change stays closed. [inferred]
- **R4:** Land takes one pull request. The pull request ships every spec whose branch name, read at the pull request's head, equals the pull request's head branch, and all of them must be closed; if any is open, land stops with a verdict that says the work is not finished and changes nothing. If no spec matches, land stops with a verdict naming that reason. Errors: no pull request given, or a pull request that is closed or already merged, each stop with a verdict naming the reason; several matching specs are legitimate and are all checked. [paraphrase]
- **R5:** Land works conflicts first, then review threads, then CI. A conflict is reported with the branch that needs a rebase, and land stops. Open threads dispatch resolve-pr in autonomous mode. Red CI in the pull request's own code gets one fix; a flaky check gets one rerun, and an identical second failure is not treated as a flake. A branch behind its base is caught up server-side. Land never rebases, force-pushes, retargets, or checks out a branch in the invoking checkout. Errors: a refused catch-up is reported as a conflict; a fix that does not turn CI green stops with the failing check named. [inferred]
- **R6:** Land merges only when the user or the calling flow authorized this pull request in the current session; otherwise it stops at merge-ready. Before merging it requires green checks, a review decision that does not block, and zero unresolved threads. When `land.mergeVerdictCommand` is set it runs once and any non-zero exit stops the run. When no human authorized the merge in-session, land waits `land.patienceMinutes` after the last push. The merge is a squash pinned to the full head SHA. Errors: a head that moved since the read refuses the merge and land re-reads; a missing, unexecutable or timed-out verdict command counts as non-zero. [inferred]
- **R7:** When the pull request has open children, land links them into a GitHub stack before merging. A stack layer merges through the asynchronous merge call with a head pin, lowest layer first, one layer per run. Land never deletes a branch an open pull request still targets. On a native stack land deletes the merged branch in a separate call after the merge is confirmed and after checking that no open pull request has it as base. Errors: when stacks are unavailable, a child that conflicts after its parent merges is reported as needing a rebase and land stops; a layer that is not the lowest open layer is refused. [inferred]
- **R8:** After a confirmed merge land writes nothing to the repository: no checkout, no commit, no push, no state file. Deleting the merged branch's remote ref is allowed, inside the merge call on the ordinary path and as the separate call of R7 on a native stack. It runs the tracker touchpoint when the bridge is configured and prints one `LAND_VERDICT` line as the last line of output. Errors: a failed touchpoint is reported in the verdict reason with the merge commit and does not change the merged verdict; rerunning land on the merged pull request repeats only the touchpoint. [inferred]
- **R9:** The following are removed from land: repo-wide discovery, the authorship probe and the footer as a gate; the ledger, the tick claim and the PID reaper; the post-merge tail with its base checkout, persist-push, rollback and re-entry; the plain-chain force-push cascade, patch-id carry-over and the pending-branch-delete list; the silence signal, the clean-review classification and the comment pattern; the reviewer request; the merge-identity override; the after-review patience key; and release-follow. The land skill's instruction text, references included, is under 200 lines. A classification preset that no caller uses after this change is removed from flowctl. Errors: a config file that still carries a retired `land.*` key loads without error and land prints one notice naming the ignored keys. [inferred]
- **R10:** Flow's landing stage passes land the pull request and the current authorization as ordinary arguments. Flow no longer resolves source and base checkouts for land and reads no land ledger. A spec that is closed with an open pull request routes to the landing offer in attended flow and to landing under a merge destination. A confirmed merge still ends the run, and consent is re-checked at each dispatch. Waiting between land runs uses the driver's cadence with no claim to release. Errors: without current authorization flow stops before merge as today; a pull request that disappeared or was closed unmerged is never replaced. [inferred]
- **R11:** The documentation gives the recipe that replaces repo-wide landing (for each open pull request where every spec whose branch name equals its head branch is closed at its head, and at least one such spec exists, run land on it), the three ways a repository tightens the review gate (instruction file, branch protection, merge-verdict command), the manual single-layer rebase for a conflicted chain child, and the upgrade notes listing every retired key and behavior with the issue it came from. The change ships as a major version. Errors: no error surface beyond R9. [inferred]

## Boundaries
<!-- scope: business -->

- Repo-wide landing is dropped from the skill; a documented recipe replaces it. [paraphrase]
- Land merges one named, authorized pull request and nothing else. Requests for more live outside land: in the repository's instruction file, its branch protection, its merge-verdict command, or its own release documentation. [inferred]
- No new flowctl subcommand for land: no status command, no wait loop, no tail command, no verdicts posted as commit statuses. [paraphrase]
- No config key for the review gate. [paraphrase]
- No release-follow in land. A release is a separate step that follows the repository's release documentation. [inferred]
- No automated rebase of a conflicted chain child. It is a documented manual step until someone needs more. [inferred]
- Landing over GitLab merge requests stays with the existing GitLab parity spec. [inferred]
- The fix for a worker that returns while its own commands are still running is a separate spec. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

- Land is too complicated for what it does. [paraphrase]
- The redesign has to fit the aim of simplifying flow-next while keeping it as capable, and the repository's agentic strategy. [paraphrase]
- Land is never required. It runs only on an explicit land invocation or an explicit merge destination on flow, so the looser default review gate reaches nobody who did not ask to merge, and documentation is the right place for stricter rules. [paraphrase]
- One known setup runs land unattended across the whole repository. It moves to the documented recipe and loses the reviewer request, the merge-identity override and the ledger budgets. That cost is accepted for a skill that stays small. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

- Rejected: moving discovery, gating and the tail into flowctl with a blocking status command. It would have turned prose machinery into code machinery while leaving the two design choices that made the machinery necessary. Fixing those choices removes the need for most of it. [inferred]
- Rejected: reading task status from the pull-request head without committing it. The committed file reads todo, so it never finds a candidate. Also rejected: counting only tasks that have runtime state (a never-claimed task has none, so a partly finished spec reads complete) and a completeness stamp in the pull-request footer (it goes stale). [inferred]
- Rejected: closing the spec immediately before the merge. It moves the head after review. Closing when the pull request is created does not. [inferred]
- Rejected: keeping a thin repo-wide mode in the skill. A second mode is how the skill grew; the recipe is the same single check run in a loop. [inferred]
- The plain-chain cascade is dropped because native stacks handled the conflicting-child case that the cascade existed for, and the cascade was the only force-push land performed. [inferred]
- The three flowctl and make-pr changes are zero-judgment writes that must behave the same with no agent present, which is the repository's test for putting work in flowctl. [inferred]

## Strategy Alignment

- Design principle "Remember the bitter lesson": the deleted machinery compensated for design choices, and the fix removes the cause. What remains deterministic is the trust rail, that a merge needs current authorization and a closed spec at the head.
- Design principle "flowctl grows only under burden of proof": no subcommand is added; two existing commands gain a zero-judgment write.
- Design principle "The owner holds the license": the caller names the pull request and grants the merge, and land infers neither.
- Track "Cross-platform parity": the skill becomes host-neutral prose with no shell state machine, and the one forge-specific piece, stacks, degrades to a reported stop.

## Parked unknowns

- Whether GitHub keeps stacks past the public preview. Only GitHub can answer; the fallback in R7 holds either way.

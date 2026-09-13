## Goal & Context

A spec that depends on another spec waits today until the parent's pull request has merged. `flow --auto` skips it with `deps unsatisfied`, backlog mode writes a `blocked` row naming the parent, and a direct `/flow-next:work` on it silently builds off the default branch with no dependency check at all. On a dependency-heavy backlog this merge wait is the serialization point: every layer costs one human merge before the next layer can start, and the build loop idles between them.

This spec removes that wait for dependent specs. When a parent spec's tasks are all done and its branch exists on the remote, a dependent spec becomes selectable. Work branches from the parent's branch tip instead of the default branch. Make-pr opens the dependent PR against the parent's branch, and on GitHub links it into the parent's stack so GitHub's stack UI shows the chain and owns sequential merge and retarget. Nothing is configured: the dependency graph flow already records is the only input, and a spec with no open parent behaves exactly as today.

The primary consumption model is human review. The build loop produces a chain of small, individually reviewed layers; a person reviews each layer's clean diff and merges from the bottom, either from GitHub's stack UI or by asking land to drive the chain (the companion spec fn-149 owns landing). Nothing in this spec merges.

Who benefits: anyone running `flow --auto` over a backlog with dependency edges, and anyone reviewing the resulting PRs. Dependent specs build as soon as their parent is built instead of as soon as it is merged, and each PR carries only its own layer.

## Vocabulary

- **Chain** is flow-next's term for a dependent PR whose base is the parent spec's branch instead of the default branch. A chain exists on any code host because it is only a branch and a base ref.
- **Stack** is GitHub's server-side object that links PRs of a chain, shows the stack map in the PR merge box, and owns sequential merge plus auto-retarget of upper layers. A stack is an enhancement of a chain, present only when the host is GitHub and the link call succeeded.
- **Chain parent** of spec S is the one spec in S's `depends_on_epics` that is still open with all tasks done. **Chain-eligible** is the state where S can branch from its parent (definition in R1).
- **Layer** is one PR in a chain or stack. **Bottom layer** is the open layer whose base is the chain's base branch (the default branch, or the branch a human chose). **Frontier** is the bottom open layer, the only one that can merge next.

## Architecture & Data Models

**No new state.** The chain is recorded by things that already exist: the dependent spec's `depends_on_epics`, the parent's `branch_name`, the dependent PR's base ref, and make-pr's footer marker `<!-- flow-next:make-pr spec=<spec-id> base=<base-ref> -->`, which already carries the base ref. Land and flow derive the chain from those; no sidecar field, no chain file under `.flow/`, and no local stack-tracking state are added. The gh-stack extension's `.git/gh-stack` tracking is never read or written.

**One predicate, one owner.** The chain-eligibility rule (R1) is evaluated in exactly one place, a read-only flowctl command (R2), and every consumer calls it: `flow --auto` selection in ready and backlog mode, attended flow's next-item ladder, `/flow-next:work` at branch creation, `/flow-next:make-pr` at base detection, and flowctl's own task-admission gate. That last consumer matters: `flowctl ready --spec`, which both work schedulers call to get the task frontier, today returns an empty frontier whenever a dependency spec is not done, so a chained spec would be selected and branched and then dispatch nothing. The gate treats the chain parent as satisfied for task admission while keeping task-level `depends_on` checks unchanged. Duplicating the jq across skill files is the failure this repo has already paid for with bash-only fences and drifting copies, so the predicate is plumbing, not prose.

**Chain identity comes from history, not from scheduling state.** Eligibility answers "may S start now"; it changes the moment the parent is marked done. The question make-pr asks later is different: "was this branch built on a parent, and where is the boundary". That answer is derived from git and the parent's PR, never from a scratch file: for each dependency D of S, a ref into D's history is obtained (the branch tip `origin/<D.branch_name>` while it exists, otherwise the merged PR's head via `refs/pull/<n>/head`), and the fork point `MB = git merge-base HEAD <D_ref>` is computed. S was chained on D exactly when `MB` is not an ancestor of the chain base: the two branches share commits that the chain base does not have. `MB` is then the boundary of the parent's work inside S, whether the parent later advanced, was squash-merged, or both. A parent that advanced after S forked still yields the same `MB`; a parent merged with a merge commit or fast-forward yields an `MB` that is on the chain base, so S is correctly not chained and needs no rewrite. When no ref into D's history can be obtained, the answer is unresolved and make-pr stops rather than guessing. `.flow/tmp/spec_base` stays what it is today, a checkout-wide, ignored scratch value for gate classification; nothing in this spec rewrites history from it.

**Data flow per dependent spec S with parent P:**

1. Selection asks flowctl whether S is chain-eligible; the answer names P and P's branch.
2. Work fetches `origin/<P.branch_name>` and creates `S.branch_name` from that tip. The recorded spec base becomes the merge-base of HEAD and the parent tip, so gate classification and the quality auditor see only S's own diff.
3. Make-pr resolves the base to P's branch when P's PR is still open, creates the PR, and on GitHub links it into P's stack (creating the stack from P's PR plus S's PR when P has none).
4. Land, flow, and humans read the chain from the PR's base ref and the marker. Landing is fn-149's contract.

**Host scoping.** Steps 1 and 2 are host-neutral. Step 3's PR creation uses the existing `gh` path; the stack link runs only when the remote is GitHub. On any other host the PR stands as a plain chain layer. This keeps the design ready for the GitLab parity work (fn-73) without touching it.

**Linear chains only.** GitHub stacks are single linear chains in one repository, and a branching chain would give two layers the same parent branch. The predicate refuses the diamond in both directions: a spec with two open parents parks, and a second child of an already-chained parent parks until the first child's PR merges (R1).

## API Contracts

### flowctl: chain eligibility (read-only)

```text
flowctl spec chain <spec-id> --json
```

Output shape (exhaustive):

```json
{
  "spec": "fn-152-example",
  "eligible": true,
  "parent": "fn-149-example",
  "parent_branch": "fn-149-example",
  "parent_branch_on_remote": true,
  "reason": "parent open, all tasks done, branch on origin"
}
```

- `eligible` is true when every entry of `depends_on_epics` is `done`, or when exactly one entry is open with all of its tasks done (a `no_plan` spec's implicit task counts), every other entry is `done`, and that parent's `branch_name` exists on `origin`. In the all-done case `parent` and `parent_branch` are `null`, `parent_branch_on_remote` is `null`, and `reason` is `no open dependency`.
- `eligible` is false, with `parent` still naming the candidate parent where one exists, when: any dependency is open with unfinished tasks (`reason`: `dependency <id> in progress`); two or more dependencies are open with all tasks done (`reason`: `two open parents: <id>, <id>; chains are linear`); the parent's branch is absent on origin (`parent_branch_on_remote: false`, `reason`: `parent branch <b> not on origin; push it or land the parent first`); another open spec already names the same parent and has a branch on the remote (`reason`: `parent <id> already chained by <sibling-id>`); or the remote query itself failed (`parent_branch_on_remote: null`, `reason`: `remote query failed: <first stderr line>`). A remote failure is never reported as an absent branch.
- Remote reads are a single `git ls-remote --heads origin` per invocation, used for both the parent-branch check and the sibling check. The command never calls `gh`.
- Exit codes: 0 on any evaluation including `eligible: false`, 2 when the spec id does not exist or `depends_on_epics` names a missing spec (the existing `validate` rule).
- A spec with an empty `depends_on_epics` returns `eligible: true, parent: null` without touching the remote. This is the byte-identical path for every spec in the repo today.

### flowctl: task admission for a chained spec

`flowctl ready --spec <id>`, `flowctl next`, and `flowctl ready` (all specs) share one spec-level dependency gate today: any dependency not `done` empties the frontier. The gate changes to: a dependency that `spec chain` reports as the spec's parent (open, all tasks done, branch on origin) counts as satisfied; every other not-done dependency still blocks. Task-level `depends_on` inside the spec is untouched. The `blockedBy` projection and the ready-gate output shapes are unchanged; only the predicate feeding them moves to the shared command. Errors: none beyond `spec chain`'s exit 2, which surfaces as the existing missing-dependency error.

### Work: branch from the parent tip

When `flowctl spec chain` names a parent, `/flow-next:work` creates the spec branch from the parent's remote tip:

```bash
git fetch origin "<parent_branch>"
git checkout -b "<branch_name>" "origin/<parent_branch>"
git merge-base HEAD "origin/<parent_branch>" > .flow/tmp/spec_base
```

- The base used for every local git operation in work (spec base, gate classification, the quality auditor's diff range) is the remote-tracking ref `origin/<parent_branch>`. Work never creates a local branch named after the parent.
- Errors: `spec chain` reporting `eligible: false` stops before any task starts with `BLOCKED: <reason from the command>`; the same reason selection already used to park the spec. This covers the unpushed parent and a failed remote query.
- `--branch=current` on a chained spec requires the current branch to contain the parent tip (`git merge-base --is-ancestor origin/<parent_branch> HEAD`); otherwise the run stops with `BLOCKED` naming the missing ancestry. Worktree mode applies the same base through the worktree kit.
- Work pushes the spec branch as it does today; nothing about publication changes on the authoring side while no PR exists.
- An explicit human `--base` on work is out of scope; the parent branch is the base whenever a parent exists.

### Make-pr: base cascade and stack link

The base-detection cascade gains one rung, evaluated after an explicit `--base` and before the default-branch rungs:

```text
--base <ref> (explicit)  ->  chain parent branch (parent PR open)  ->  origin/main -> main -> origin/master -> master -> ask
```

- **Chain detection** runs once in Phase 0, after the spec id is known and before base validation, and tests history rather than scheduling state. For each dependency D of the spec, in `depends_on_epics` order: obtain `D_ref` as `origin/<D.branch_name>` after a fetch when the branch exists on origin, otherwise as the head of D's merged PR fetched via `refs/pull/<n>/head`. Compute `MB = git merge-base HEAD D_ref`. The branch is chained on D when `git merge-base --is-ancestor MB origin/<chain_base>` is false, and `MB` is the boundary. The first chained D wins. No chained D means the cascade continues to the default-branch rungs untouched. A D that is open with all tasks done but whose history cannot be reached (no branch on origin and no merged PR), or a merged D whose PR head cannot be fetched, is unresolved: make-pr exits 2 with `NEEDS_HUMAN: cannot establish the chain boundary for <D>; parent history unreachable`, and never rewrites or opens a PR on a guess.
- **Parent PR open:** the chain rung sets `BASE_REF=origin/<parent_branch>`. Every local validation and diff range uses that remote-tracking ref (it exists after the fetch on any clone, whether or not the parent is checked out locally); only the `--base` argument passed to `gh pr create` strips `origin/`, which the existing create path already does.
- **Parent PR merged:** the dependent branch still carries the parent's pre-squash commits, and a PR against the chain base would double-count them. On a **create** run only, make-pr rewrites the branch before opening the PR: `git rebase --onto origin/<chain_base> <boundary>`, where the boundary is the ancestor SHA found by chain detection, never a scratch value. Preconditions, all verified inside the same fence: no open or merged PR exists for this branch (the existing Phase 0 probe has already run); the run is not `--dry-run` and not `--update`; the boundary SHA is an ancestor of HEAD; the working tree is clean. If the branch is already on origin, publication is `git push --force-with-lease=<branch>:<remote_sha> origin <branch>` after an `ls-remote` read of `<remote_sha>` equal to the pre-rebase HEAD; a lease failure aborts with `NEEDS_HUMAN: <branch> moved on origin during rewrite`. A rebase conflict aborts the rebase, restores the pre-rebase HEAD, and exits 2 with `NEEDS_HUMAN: parent <id> merged; rebase <branch_name> onto <chain_base> conflicts in <files>`. This is the only history rewrite outside land, and it is bounded to a branch with no PR.
- **`--dry-run` with a merged parent** performs no rewrite and no push; it prints `would rebase <branch> onto <chain_base> from <boundary>` on stderr and renders the body against the current diff. **`--update`** never rewrites; it edits the existing PR as today, and a merged parent under `--update` is land's retarget case (fn-149), not make-pr's.
- **Parent PR closed without merge:** exit 2 with `NEEDS_HUMAN: parent <id> PR #<n> closed unmerged; the chain is broken`.
- **Parent has all tasks done but no PR yet:** the base is `origin/<parent_branch>` (it exists on origin, per work's precondition); no stack link is attempted because there is no parent PR to link to, and the body's stack line is omitted.
- Branch validity keeps today's rules (merge-base exists, at least one commit past it). The base is still not required to be an ancestor of HEAD.

After a successful `gh pr create`, on a GitHub remote, with the base resolved by the chain rung:

```bash
STACK=$(gh api "repos/{owner}/{repo}/stacks?pull_request=<parent_pr_number>" --jq '.[0] // empty')
# parent already in a stack (the API takes an integer array; -F types numbers, -f would send strings):
gh api --method POST "repos/{owner}/{repo}/stacks/<stack_number>/add" -F 'pull_requests[]=<new_pr_number>'
# parent not in a stack:
gh api --method POST "repos/{owner}/{repo}/stacks" -F 'pull_requests[]=<parent_pr_number>' -F 'pull_requests[]=<new_pr_number>'
```

- Success (200 or 201) adds one line to the PR body's summary block, sourced from the response, in exactly this shape: `**Stack:** #<stack number>, layer <position> of <size>`. No other stack text appears in the body; the guardrail against invented references applies.
- Failure is never fatal to PR creation. On 404 (stacks unavailable on this repo), 409 (concurrent modification), 422 (the parent's base does not chain, or the PR is already elsewhere), or any transport error, make-pr prints one stderr line `stack link skipped: HTTP <code> <message>` and the PR stands as a plain chain layer. It never retries in the same run and never unstacks anything.
- The `--base` flag passed to `gh pr create` strips a remote prefix exactly as today.

### Draft or ready for chained layers

A chained layer is created **ready** when its open-items count is zero, including under autonomous drivers, as a documented exception to forced draft. Reason: a human merging from the stack UI cannot merge a draft, and land flips ready only immediately before its own merge. Open items still force draft; an explicit `--draft` always wins. Non-chained PRs keep today's four-input matrix unchanged. Land's draft-review trigger (which fires only on drafts) therefore never fires for a ready chained layer; the review bots' open-for-review trigger covers it.

### Selection and verdicts

- `flow --auto` ready mode replaces its dependency conjunct (every dependency `done`) with `flowctl spec chain` reporting `eligible: true`. Any `eligible: false` parks the candidate with the command's `reason`, records no strike, and preserves readiness; an unpushed parent and a failed remote query therefore park at selection instead of being dispatched into a block. Backlog mode's Phase 1.5 and the 1.6 `dep-unsatisfied` triage use the same call; the `blocked` decision-log row keeps its shape and now carries the `reason` string from the command. Selection still makes no `gh` call; the command's single `git ls-remote` is the only remote read.
- Attended flow's next-item ladder (the "next open spec by readiness, order, and dependencies" step) applies the same command instead of judgement when a candidate has dependencies.
- The branch matrix row `work + branch absent -> --branch=new` passes the parent through to work; no new row is added.
- The `PILOT_VERDICT` line keeps its shape. For a chained spec the `reason` string starts with `chained on <parent-id>; ` followed by the existing reason text. The decision-log row for a chained dispatch carries the same prefix in its reason.

## Edge Cases & Constraints

- **Parent revised after the child branched.** Any push to the parent branch after the child forked moves the child's merge-base. Nothing in this spec reacts; land's chain retarget and patch-id carry-over (fn-149) re-base the child when the parent merges, and a reviewer sees the child's own diff against the parent branch throughout. This is the one cost the serial model never paid: a parent reworked heavily after review may leave the child needing a rebase, or discarded if the parent dies.
- **Parent closed unmerged.** The child's PR base still exists as a branch. Make-pr refuses to open a new chained PR on it (above); an already-open child is land's `chain broken` case.
- **Branch deletion.** A parent branch must not be deleted while a child PR targets it. That rule lives in land (fn-149). This spec adds the guard on the authoring side: work's `--branch=new` never deletes or resets an existing parent branch, and make-pr never passes a delete flag.
- **Depth.** Chains may nest (a spec whose parent is itself chained). GitHub documents no maximum stack size. No cap is added; the linear rule alone bounds the shape.
- **Forks.** GitHub stacks require every branch in one repository. Flow-next PRs are same-repo already; a fork-based remote leaves the link call to fail with 422 and the PR stands as a plain chain layer.
- **Required checks.** GitHub evaluates every layer's merge requirements against the stack's base branch, and `pull_request` workflows run for every layer. CI cost per layer is unchanged from a plain PR.
- **Concurrency.** Two `flow --auto` drivers on one clone are already excluded by task-level claims. Two children racing for one parent are excluded by the sibling rule in R1, which reads remote branches, so a sibling that has not pushed yet is not visible; the race window is the time between branch creation and first push, and the loser of that race discovers it at make-pr's stack link (422) and stands as a plain chain layer. This is accepted and documented rather than locked.
- **Preview status.** GitHub labels stacked pull requests public preview and "subject to change". Every stack-specific call in this spec degrades to a plain chain on failure, so a shape change costs a stderr line, never a broken PR.
- **Backward compatibility.** A repo with no dependency edges never reaches any new code path. Existing specs with dependencies all `done` evaluate to `parent: null` and take the old cascade.

## Acceptance Criteria

- **R1:** A dependent spec is chain-eligible when every dependency is done, or when exactly one dependency is open with all of its tasks done and the rest are done, and no other open spec with a remote branch already names that parent. Errors: two open parents refuses with both ids named; a parent with unfinished tasks refuses naming it; a sibling already chained refuses naming the sibling. Every refusal is a reason string, never a strike.
- **R2:** `flowctl spec chain <spec-id> --json` evaluates R1 and prints the exhaustive shape above, including parent-branch availability on origin and a distinct remote-failure outcome. Errors: unknown spec or a dependency naming a missing spec exits 2 with the existing validate message; a remote query failure is `eligible: false` with `parent_branch_on_remote: null`, never reported as an absent branch; a spec with no dependencies returns `eligible: true, parent: null` with no remote read.
- **R2a:** flowctl's spec-level task-admission gate (`ready --spec`, `next`, `ready`) treats the chain parent reported by R2 as a satisfied dependency, so a selected and branched chained spec dispatches its tasks; every other not-done dependency still empties the frontier, and task-level `depends_on` is unchanged. Errors: none beyond R2's exit 2.
- **R3:** `flow --auto` in ready and backlog mode selects a spec only when R2 reports `eligible: true`, and parks it with R2's reason otherwise, without a strike and preserving readiness. Attended flow's next-item ladder applies the same command. Errors: none beyond R2; a parked spec is a reason string, never `NEEDS_HUMAN`.
- **R4:** `/flow-next:work` on a chained spec creates the spec branch from the parent's fetched remote-tracking ref, uses that ref for the spec base, gate classification, and the auditor's diff range, and never creates a local branch named after the parent. Errors: an `eligible: false` from R2 blocks before any task starts with the command's reason; `--branch=current` without the parent tip in its ancestry blocks naming the missing ancestry.
- **R5:** Make-pr detects a chained branch from history (the merge-base of HEAD with a dependency's branch tip or merged-PR head that is not on the chain base), which identifies the parent and the boundary together and survives a parent that advanced after the fork; an unreachable parent history exits 2 as unresolved rather than guessing. It resolves the base to the parent's remote-tracking ref when the parent's PR is open, keeps an explicit `--base` above it, and leaves the default cascade byte-identical when no ancestor is found. Errors: parent PR merged, on a create run only, rewrites the branch onto the chain base from the detected boundary with a clean-tree precondition and a leased push when the branch is on origin, and exits 2 on conflict naming the files or on a lease failure; `--dry-run` and `--update` never rewrite or push; parent PR closed unmerged exits 2 naming the PR; parent with no PR uses the parent branch as base with no link attempt. Switching branches between work and make-pr, a missing scratch file, or a fresh clone changes nothing, because no scratch value feeds the rewrite.
- **R6:** On a GitHub remote, after creating a chained PR whose parent has an open PR, make-pr links it into the parent's stack via the stacks REST endpoints with integer-typed `pull_requests` (add when a stack exists, create from parent plus child otherwise) and writes the single `**Stack:**` body line from the response. Errors: 404, 409, 422, and transport failures print one stderr line and leave a plain chain layer; no retry, no unstack, PR creation never fails because of the link.
- **R7:** On a non-GitHub remote the stack link is skipped silently and the PR is a plain chain layer; no GitHub-only call runs. No error surface beyond the existing host detection.
- **R8:** A chained layer with zero open items is created ready, including under autonomous drivers; open items still force draft; an explicit `--draft` wins; non-chained PRs keep the existing draft matrix byte-identically. No error surface beyond the existing matrix.
- **R9:** The `PILOT_VERDICT` reason and the backlog decision-log row for a chained dispatch begin with `chained on <parent-id>; `. Non-chained runs print byte-identical lines. No error surface beyond R3.
- **R10:** No configuration key is added or read. `flowctl config` output, `get_default_config()`, the generated schema, and the schema drift test are unchanged by this spec. No error surface.
- **R11:** The gh-stack extension is never required, invoked, or detected; its local state is never read. No error surface.
- **R12:** Documentation: the orchestration and teams pages describe chains and stacks in the vocabulary above (chain on any host, stack on GitHub, linear only, human merges from the bottom, the parent-reworked cost); the make-pr and work skill references gain the chain rung and the parent-tip branch rule; the glossary gains `chain`, `stack`, `layer`, and `frontier`; the changelog carries the entry under Unreleased. The stacked-PR recovery memory entry from 2026-08-27 is updated to point at the chain rules instead of the manual successor-PR playbook. No error surface.
- **R13:** Verification covers every consumer, not only the predicate. Disposable git fixtures (temporary repositories with a bare `origin`) exercise: the R2 states including the unpushed parent, the sibling refusal, and a remote failure; the R2a task-admission gate with an open parent; work's branch ancestry for `--branch=new` and `--branch=current`; make-pr's chain detection from an open parent branch and from a merged-PR head, including a parent that advanced after the child forked both before and after its squash merge, a merge-commit parent that needs no rewrite, and an unreachable parent history; the merged-parent rewrite including a conflict, a lease failure, a switched branch, a missing scratch file, and the no-rewrite guarantee under `--dry-run` and `--update`. A stubbed `gh` records the stack requests and asserts integer-typed payloads plus each degrade code; the draft matrix and the verdict prefix are asserted per consumer; and a fixture with no dependency edges asserts byte-identical cascade, draft, and verdict output. Tests pin behaviour and shapes, never prose (the repo's G2 rule). No error surface.

## Boundaries

- No merge, retarget, rebase-after-merge, branch deletion, or patch-id logic. Landing a chain is fn-149.
- No stack restructuring: reorder, fold, insert, or unstack. A human uses GitHub's UI or the gh-stack extension for those; flow-next never dissolves a stack it created.
- No merge-queue enrolment and no auto-merge arming.
- No local stack-tracking files, no gh-stack dependency, no Graphite or other stacking tool.
- No cross-repository or fork chains.
- No `--base` on `/flow-next:work`; the parent branch is the only chain base.
- No release batching: each merged layer runs the same post-merge tail as any PR today.
- No GitLab merge-request chaining; the host-neutral predicate and branch rule leave the door open for fn-73 and nothing more.

## Decision Context

### Motivation

Stacking was first designed in July as an opt-in gated by a config key, with the GitHub stack API as the only mechanism and land hardening as a prerequisite. Three things changed the design. Field evidence on 2026-08-27 showed what a hand-built chain costs when the tooling does not understand it: squash-merging the base with branch deletion closed the dependent PR permanently, and recovery took a rebase, a force-push, and a successor PR. A survey of an established autonomous stacking playbook showed that plain branch-on-branch chains with a single topology writer work on any forge, and that the native API is an accelerator rather than a requirement. And re-verification of GitHub's stacks API on 2026-09-13 showed the July shapes intact plus a client-side head pin on the asynchronous merge endpoint, which removes the largest safety objection to native merging.

The result is one behaviour with no switch: a chain is the default shape for a dependent spec, the stack is a free upgrade on GitHub, and the only observable cost, a child that needs a rebase when its parent is reworked, is stated in Edge Cases instead of hidden behind "no drift for non-adopters".

### Implementation Tradeoffs

- **Predicate in flowctl, not skill prose.** Four consumers need one answer. Prose copies drift; the repo's own memory records the cost of duplicated bash across skills. The command is read-only and makes no network call beyond `git ls-remote`.
- **No new sidecar field.** The PR's base ref and the make-pr marker already record the chain, so a field would be a second source of truth that could disagree with GitHub. Deriving from the PR keeps land honest on a chain a human stacked by hand.
- **REST over the gh-stack extension.** `gh api` is authenticated on every install that can open a PR; the extension adds an install step, a version surface, and local state for no gain at the link layer. Its `link` subcommand does the same REST calls, so the two interoperate.
- **Born ready for chained layers.** Forced draft under autonomy exists so a human flips a PR ready after deciding it is worth review. In a chain the human's decision moves to merging the layer, and a draft cannot be merged from the stack UI. The exception is scoped to chained layers with zero open items.
- **Linear only, refuse the diamond.** GitHub stacks are linear. Allowing a plain-chain diamond on non-GitHub hosts would create two behaviours for one predicate; refusing everywhere keeps R1 host-neutral and simple.
- **Rebase-onto in make-pr for the merged-parent window.** The alternative was to refuse and route to land. Refusing leaves a fully built spec stuck for a human, while the rebase is safe before a PR exists and is the same operation land performs later with a lease.
- **Single release with fn-149.** Both specs ship in one release. fn-149 merges first; this spec's own PR is built as a chain layer on fn-149's branch (base set by hand, since the authoring path is what this spec builds), which gives land its first live chain to babysit before either is released.

## Resolved via Research

Written by the flow conductor's research pass on 2026-09-13; live probes against the July smoke repository and the GitHub docs, no scouts.

- GitHub stacks REST endpoints: `GET /repos/{owner}/{repo}/stacks?pull_request=<n>`, `POST /repos/{owner}/{repo}/stacks` with `pull_requests` ordered bottom to top, `POST .../stacks/{stack_number}/add`, `POST .../stacks/{stack_number}/unstack`; each PR's base ref must match the previous PR's head ref; API version header `2026-03-10`. Source: https://docs.github.com/en/rest/pulls/stacks
- The REST pull request payload carries a `stack` object (`id`, `number`, `position`, `size`, `base.ref`) and `null` for standalone PRs; `gh pr view --json` does not expose it. A webhook `stacked` action fires when a PR first joins a stack, and `github.event.pull_request.stack` is available to workflows. Source: https://docs.github.com/en/pull-requests/tutorials/roll-out-stacked-prs
- Stacks are linear, same-repository only, no forks; branch protection, required checks, and CODEOWNERS are enforced on every layer against the stack's base branch; `pull_request` workflows run for every layer; feature is public preview and subject to change. Source: https://docs.github.com/en/pull-requests/get-started/about-stacked-prs
- Live on 2026-09-13: the stack created on 2026-07-31 in the smoke repository still reads back with the same shape, and a plain dependent PR whose parent merged without branch deletion stayed open until closed by hand a month later. Source: `gh api repos/gmickel/stacks-api-smoke/stacks` and `.../pulls/6`
- Branch deletion, not the squash, closed the dependent PR in the 2026-08-27 incident. Source: `.flow/memory/knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27.md`
- The gh-stack extension keeps stack state in `.git/gh-stack`, pushes with `--force-with-lease`, and its `link` subcommand creates or extends a stack from existing PRs without local tracking. Source: https://docs.github.com/en/pull-requests/reference/stacked-prs-cli-commands
- Make-pr's footer marker already carries `base=<base-ref>`, and land's authorship probe keys on it. Source: make-pr workflow, footer section; land workflow, authorship probe.

## Parked unknowns

- GitHub's merge-queue support for stacks was "rolling out progressively" at announcement; flow-next never enrols a queue, so nothing here depends on it, but a repo with a required queue on the default branch has not been exercised with a chain.

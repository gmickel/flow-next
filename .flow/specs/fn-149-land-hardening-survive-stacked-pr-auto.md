## Conversation Evidence

> user (turn 1): "https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ [...] research task. how does this help flow-next, and does it conflict with our new make-pr or does it improve it"
> user (turn 2): "capture it, probable 2 specs, then commit and push so we have the specs stored. [...]"
> user (turn 4): "yes, capture the v0 slice and rewrite fn-150 so that we could feasibly land all 3 tomorrow so that all flow-next stuff including automonmy (pilot) etc could work as this is the biggest gain imo, also do your research properly and smoketest the api in a new test repo so we are not guessing at all."
> user (turn 5): "maybe land doesn't make sense as a flow here anyhow, would us say the point of stacked PRs is to improve being able to land lots of stuff and then review them manually? how would that change the picture"
> user (turn 6): "yes, should be --ready probably, update our specs with these new insights"

Smoke-tested live 2026-07-31 in a throwaway repo (gmickel/stacks-api-smoke) - findings that harden this spec from analysis into verified fact:
- `gh pr merge` (REST/GraphQL mergePullRequest) is HARD-BLOCKED on any stacked PR: "This pull request is part of a stack and must be merged sequentially using the stack merge API." Land's current merge call cannot merge a stacked PR at all.
- The stack merge API is `PUT /repos/{o}/{r}/pulls/{number}/merge-async` with `{"merge_method": "squash", "merge_action": "direct_merge"}`; it is asynchronous (status pending, then merged/enqueued/failed; poll `GET .../merge-async/{uuid}`). It also works on non-stacked PRs.
- CONFIRMED COLLAPSE HAZARD: calling merge-async on an upper layer merges ALL unmerged layers below it, sequentially, each as its own squash commit. Only the bottom-most open layer is safe to target.
- merge-async has NO client-supplied head pin (no equivalent of the match-head-commit guard in the request); the submit response echoes the server-captured `expected_head_sha`.
- After a bottom-layer merge, GitHub auto-rebases upper layers (head SHAs move) and retargets their bases; the timeline attributes the force-push to the account that requested the merge, not a bot.
- Stack membership is readable from the raw REST PR payload's `stack` object ({number, position, size}); `gh pr view --json` does not expose it - reads must use `gh api`. Merge-async on a draft PR fails cleanly ("Pull request is in draft").

## Goal & Context

<!-- Source-tag breakdown: 15% [user], 55% [paraphrase], 30% [inferred] -->

The land skill babysits build-loop-authored PRs with gates anchored to head SHAs and push timestamps: merge uses a match-head-commit guard, stale-approval detection compares review SHAs to head, the clean-review-comment signal must name the current head SHA, and the reviewer patience window is anchored to the last push. GitHub's stacked-PRs preview (2026-07-30) breaks two of land's assumptions, both verified live: (1) server-initiated head and base movement after a lower layer merges makes SHA-anchored gates misread retargets as reviewer activity or violated head-match; (2) land's merge call itself is rejected on stacked PRs, which must be merged via the asynchronous stack merge endpoint - and targeting the wrong layer merges everything below it.

This spec makes land correct on stacked PRs: recognize retargets and re-gate, merge stacked PRs via the right endpoint targeting only the bottom-most open layer, and stay byte-identical for non-stacked PRs. It pays even before flow-next authors stacks (a human or another tool can stack a flow-authored PR), and it is the prerequisite for the make-pr stack-linking slice and the pilot stacking spec (fn-150).

## Acceptance Criteria

- **R1:** A land tick detects that a babysat PR's base branch changed since the previous tick (retarget) and classifies it as a re-verify event: gates re-read against the new base, no NEEDS_HUMAN solely for the base change. [paraphrase]
- **R2:** A head SHA that moved without an authored push (server-side auto-rebase) does not hard-fail the merge path: land re-reads the current head, re-runs the gate tree against it, and only then decides an action - never merges against a stale recorded head. [paraphrase]
- **R3:** The reviewer patience window does not treat the stack-retarget force-push as reviewer-relevant activity in a way that lets an auto-retargeted PR wait indefinitely in AWAITING_REVIEW. [inferred]
- **R4:** Land reads stack membership from the PR's REST payload (the `stack` object via `gh api`; `gh pr view --json` does not carry it). A stacked PR that is NOT the bottom-most open layer is never merged this tick - land reports it as awaiting its lower layers. [paraphrase]
- **R5:** Land merges a stacked PR (bottom-most open layer, all gates green) via the stack merge endpoint (merge-async, squash, direct merge): submit, verify the response's server-captured expected head SHA equals the head land's gates just evaluated (mismatch is NEEDS_HUMAN - the endpoint has no client-side head pin), poll to a terminal status within the tick's bounded budget, and record the outcome. `pending` beyond budget is reported and re-checked next tick, never re-submitted blindly. [paraphrase]
- **R6:** Non-stacked PRs keep the existing merge call and guard byte-identically (stack absent means zero behavior change). [paraphrase]
- **R7:** Behavior for non-stacked PRs is unchanged across the whole gate tree - identical verdicts and ledger writes (R4's stack read adds one `gh api` PR fetch to every tick, folded into an existing fetch where possible; verdict-affecting behavior is byte-identical). [inferred]
- **R8:** The catch-up conflict rule is unchanged: a conflict produced by a stack retarget is BLOCKED, never hand-resolved. *(AMENDED by fn-194/#342: §3.3 is now server-side `gh pr update-branch` - no local rebase exists; GitHub's refusal IS the conflict verdict. Re-plan this R against the new §3.3 before implementing.)* [paraphrase]

## Boundaries

- No flowctl Python changes: all gates, the stack read, and the R5 merge-async submit/poll loop are land-skill prose + `gh api` bash in workflow.md (like the existing merge block) - never a flowctl poller.

- No stack authoring anywhere in this spec - creating/linking stacks is the make-pr v0 slice; pilot orchestration is fn-150. [user]
- No dependency on the gh-stack CLI extension; everything is plain gh/REST. [paraphrase]
- No merge-queue integration (`merge_action` stays direct merge; queue enrollment remains forbidden). [paraphrase]
- Docs: the land skill reference gains a stacked-PRs section (collapse hazard, merge-async contract, retarget re-gate); no public vocabulary changes. [inferred]

## Decision Context

Why now: verified live that land's current merge call cannot merge a stacked PR and that targeting an upper layer collapses the stack - so without this spec, land is broken or dangerous the moment any babysat PR joins a stack, regardless of who stacked it. Hardening the reader and fixing the merge path are independent of, and prerequisite to, authoring stacks. The no-client-head-pin gap in merge-async is mitigated by minimizing the read-to-submit window and verifying the server-echoed expected head SHA, with mismatch escalating to NEEDS_HUMAN rather than proceeding. [paraphrase]

Driver scoping: in the default human-merge flow (merging layers from GitHub's stack UI) land never merges, so R5 is exercised only when the user chooses land as the driver - running land IS choosing autonomous merging, no extra gate needed. R1-R4 protect every land tick regardless: human merges cause the retargets that land then observes while babysitting CI and review threads on the remaining layers. [paraphrase]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | TBD - populate via /flow-next:plan |
| R2 | TBD - populate via /flow-next:plan |
| R3 | TBD - populate via /flow-next:plan |
| R4 | TBD - populate via /flow-next:plan |
| R5 | TBD - populate via /flow-next:plan |
| R6 | TBD - populate via /flow-next:plan |
| R7 | TBD - populate via /flow-next:plan |
| R8 | TBD - populate via /flow-next:plan |

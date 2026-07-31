## Conversation Evidence

> user (turn 1): "https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ [...] research task. how does this help flow-next, and does it conflict with our new make-pr or does it improve it"
> user (turn 2): "capture it, probable 2 specs, then commit and push so we have the specs stored. other agents working here too, don't interfere with each other"

Research findings this capture rests on (agent research, 2026-07-31, from the GitHub changelog + stacked-PRs quickstart docs): GitHub stacked PRs entered public preview 2026-07-30. When a lower layer of a stack merges, GitHub automatically rebases and retargets the upper PRs - their head SHAs move and their base branch changes without any human or agent push. Merging the topmost ready PR lands it plus all unmerged layers below in one operation.

## Goal & Context

<!-- Source-tag breakdown: 20% [user], 50% [paraphrase], 30% [inferred] -->

The land skill babysits build-loop-authored PRs with gates anchored to head SHAs and push timestamps: merge uses a match-head-commit guard, stale-approval detection compares review SHAs to head, the clean-review-comment signal must name the current head SHA, and the reviewer patience window is anchored to the last push. GitHub's stacked-PRs preview (2026-07-30) introduces server-initiated head and base movement: after a lower stack layer merges, GitHub auto-rebases and retargets upper PRs. Those events look, to land's current gates, like reviewer activity or like a violated head-match - producing spurious BLOCKED/NEEDS_HUMAN verdicts, stale-approval churn, or a patience window that never expires.

This spec hardens land so a retargeted or server-rebased PR is recognized and re-gated instead of misread. It is cheap insurance that pays even before flow-next ever authors stacks: GitHub controls the retarget, and a repo adopting stacks around flow-next PRs must not break the ship loop. Authoring stacks is explicitly out of scope here (see the companion pilot-stacking spec).

## Acceptance Criteria

- **R1:** A land tick detects that a babysat PR's base branch changed since the previous tick (retarget) and classifies it as a re-verify event: gates re-read against the new base, no NEEDS_HUMAN solely for the base change. [paraphrase]
- **R2:** A head SHA that moved without an authored push (server-side auto-rebase) does not hard-fail the merge path: land re-reads the current head, re-runs the gate tree against it, and only then decides an action - never merges against a stale recorded head. [paraphrase]
- **R3:** The reviewer patience window distinguishes GitHub-initiated rebase pushes from authored pushes so an auto-retargeted PR cannot wait indefinitely in AWAITING_REVIEW due to window resets it did not cause. [inferred]
- **R4:** Land never uses the stack collapse merge (merging an upper layer to land all layers below in one operation). Stacked PRs merge bottom-up only, one layer per tick, preserving the one-action-per-PR and every-gate-per-PR contract; this is recorded as a forbidden behavior in the skill. [inferred]
- **R5:** Behavior for non-stacked PRs is unchanged - a repo that never uses stacks sees identical gate reads, verdicts, and ledger writes. [inferred]
- **R6:** The mechanical-rebase conflict rule is unchanged: a conflict produced by a stack retarget aborts to BLOCKED, never hand-resolved. [paraphrase]

## Boundaries

- No stack authoring anywhere in this spec - make-pr, pilot, and work do not create stacks (companion spec owns that, preview-gated). [user]
- No dependency on the gh-stack CLI extension; land hardening must work with plain gh reads. [inferred]
- No merge-queue integration work (GitHub is still rolling that out for stacks). [inferred]
- Docs: the land skill reference gains a short stacked-PRs note; no public vocabulary changes. [inferred]

## Decision Context

Why now: GitHub shipped the preview 2026-07-30; the failure mode (server-moved heads/bases) can hit any repo where land babysits PRs, regardless of whether flow-next authored a stack - other tools or humans in the same repo can create the conditions. Hardening the reader is independent of, and prerequisite to, ever authoring stacks. [paraphrase]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | TBD - populate via /flow-next:plan |
| R2 | TBD - populate via /flow-next:plan |
| R3 | TBD - populate via /flow-next:plan |
| R4 | TBD - populate via /flow-next:plan |
| R5 | TBD - populate via /flow-next:plan |
| R6 | TBD - populate via /flow-next:plan |

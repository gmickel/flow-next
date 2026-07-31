## Conversation Evidence

> user (turn 1): "https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ [...] research task. how does this help flow-next, and does it conflict with our new make-pr or does it improve it"
> user (turn 4): "yes, capture the v0 slice and rewrite fn-150 so that we could feasibly land all 3 tomorrow so that all flow-next stuff including automonmy (pilot) etc could work as this is the biggest gain imo, also do your research properly and smoketest the api in a new test repo so we are not guessing at all."

Smoke-tested live 2026-07-31 (gmickel/stacks-api-smoke): merging a stack's bottom layer causes GitHub to auto-rebase upper layers (head SHAs move) and retarget their bases - server-initiated, with the force-push attributed to the merging account. Merging an upper layer via the stack merge endpoint merges ALL unmerged layers below it sequentially, each as its own squash commit. Stack membership is readable per-PR from the REST payload's `stack` object. Ordinary `gh pr merge` is hard-blocked on stacked PRs.

## Goal & Context

<!-- Source-tag breakdown: 25% [user], 55% [paraphrase], 20% [inferred] -->

The merge-wait stall is the main serialization point in multi-spec autonomous runs: pilot parks a ready spec whose dependency PR has not merged. With the make-pr stack-linking slice (companion v0 spec) and land's stacked-merge hardening (fn-149) in place, pilot can drain dependent specs onto their parent's branch as stack layers - the build loop keeps producing while the ship loop babysits the whole stack bottom-up. This spec is the autonomy integration: pilot's selection, branch matrix, and verdicts understand stacking, end to end, so the full pipeline (including backlog mode) works over stacks. This is the biggest gain of the stacked-PRs feature for flow-next. [user]

All three specs (fn-149, the v0 make-pr slice, this one) are scoped to be landable together immediately - no deferral. The earlier preview-stability deferral is dropped: the API surface was verified live, the opt-in gate contains the blast radius, and worst-case API regressions degrade to today's serial behavior. [user]

## Acceptance Criteria

- **R1:** With `stacks.enabled` on and the repo GitHub-hosted, pilot (interactive-select and backlog mode) can select a ready spec whose flow dependency has an open unmerged PR, instead of parking it - provided the dependency spec's tasks are all done. The work stage branches from the dependency's branch; make-pr then links the layer (companion v0 spec). In-flight dependencies (tasks not all done) still park exactly as today. [paraphrase]
- **R2:** Pilot's branch matrix and all-done PR probe operate correctly when a spec branch's parent is another spec branch rather than the default branch. [paraphrase]
- **R3:** Dependency chains only: stacking applies to linear parent chains. A diamond (two ready specs depending on the same unmerged parent) stacks the first and parks the second with a stated reason, since GitHub stacks are linear. [inferred]
- **R4:** Pilot verdict lines and the pilot log carry stack context (parent spec and layer position) so the driver transcript shows what was stacked on what. [inferred]
- **R5:** With the gate off, on a non-GitHub host, or when stack linking degraded (v0 spec R5), pilot behaves exactly as today: dependent specs park until the parent merges. No behavior drift for non-adopters. [user]
- **R6:** Land ticks over a stacked chain converge without human input in the happy path: bottom layer merges, upper layers re-gate after the server retarget (fn-149), and the chain drains over successive ticks. Covered by an end-to-end smoke scenario in the local-dev harness docs. [paraphrase]
- **R7:** Documentation: orchestration and teams docs describe the stacked flow (opt-in, GitHub-only, linear chains); the docs-site gets the story entry. Dependency-planning guidance notes that plan-created dep chains become stack chains when the gate is on. [inferred]

## Boundaries

- Requires fn-149 (land stacked-merge + retarget hardening) and the v0 make-pr stack-linking spec; this spec adds no merge or linking mechanics of its own. [paraphrase]
- Opt-in stays opt-in: never the default; enabling is an explicit user config action. [user]
- GitHub only; GitLab MR trains and other hosts are out of scope (fn-73 unaffected). [user]
- No merge-queue integration; no gh-stack extension dependency; no stack restructuring. [paraphrase]
- No flowctl Python changes expected - dep info (`flowctl dep`), branch names, and spec state already exist; pilot logic is skill prose. [paraphrase]

## Decision Context

Motivation: this directly serves the one-dial-to-autonomous claim - removing the merge-wait stall multiplies pilot backlog throughput on dependency-heavy backlogs without weakening any gate (per-layer checks, reviews, and land's gate tree still apply to every layer). Deferral dropped deliberately: the risky unknowns (API shapes, collapse semantics, retarget attribution) were eliminated by live smoke testing rather than waiting for the preview label to drop; the opt-in gate plus graceful degrade bound the residual preview risk to zero-behavior-change for non-adopters. [paraphrase]

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

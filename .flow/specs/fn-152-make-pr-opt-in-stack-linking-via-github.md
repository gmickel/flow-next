## Conversation Evidence

> user (turn 3): "could be a selling point to have early optional support for this. analyse if this would be possible without blowing up flowctl, our skills etc. we obviously wouldn't want to make it the default and we support more than just github anyhow, so optional. consider the lowest friction way, including users have to install the gh stacked commit skill that was mentioned or us taking some of that to enable this early"
> user (turn 4): "yes, capture the v0 slice and rewrite fn-150 so that we could feasibly land all 3 tomorrow so that all flow-next stuff including automonmy (pilot) etc could work as this is the biggest gain imo, also do your research properly and smoketest the api in a new test repo so we are not guessing at all."
> user (turn 5): "maybe land doesn't make sense as a flow here anyhow, would us say the point of stacked PRs is to improve being able to land lots of stuff and then review them manually? how would that change the picture"
> user (turn 6): "yes, should be --ready probably, update our specs with these new insights"

Smoke-tested live 2026-07-31 in a throwaway repo (gmickel/stacks-api-smoke), not guessed:
- `POST /repos/{o}/{r}/stacks` with `{"pull_requests": [bottom..top]}` links EXISTING plain PRs (created via `gh pr create --base <parent-branch>`) into a server-side stack. No gh-stack extension involved. 201 + stack object.
- `POST /repos/{o}/{r}/stacks/{n}/add` extends a stack upward; `GET /repos/{o}/{r}/stacks?pull_request=N` finds a PR's stack; `POST .../unstack` dissolves.
- The raw REST PR payload carries a `stack` object ({number, position, size, base}); `gh pr view --json` does NOT expose it - reads must use `gh api`.
- Draft PRs stack fine (make-pr's default-draft flow is compatible).
- Errors are clean 404/422 with actionable messages; wrong membership refuses, nothing partial.

## Goal & Context

<!-- Source-tag breakdown: 30% [user], 50% [paraphrase], 20% [inferred] -->

Early, optional stacked-PR support is a differentiator (GitHub shipped the public preview 2026-07-30; agent products are announcing day-one support) and the groundwork for removing the build loop's merge-wait stall. The primary consumption model is human review: the point of stacks is that the pipeline can produce lots of small, individually proven layers and a human reviews each layer's clean diff (stack map + per-layer cognitive-aid body) and merges from GitHub's stack UI, which owns sequential merging and retargeting. Autonomous merging (land) is a separate, opt-in tail. The lowest-friction v0 lives entirely in make-pr: flow-next already creates correctly-shaped dependent PRs via the base-ref override, and the verified Stacks REST API turns such a PR into a real stack layer with one `gh api` call after create. Zero flowctl changes, zero new dependencies (the gh-stack CLI extension is NOT required - stack linkage is plain REST via the `gh` CLI every install already has), zero behavior change while the gate is off.

## Acceptance Criteria

- **R1:** A `stacks.enabled` config gate, default off. Off or unset means byte-identical make-pr behavior and output (single config read only). [user]
- **R2:** The gate is additionally scoped to GitHub-hosted repos: on any other code host the feature is silently inactive - flow-next supports more than GitHub and this must stay true. [user]
- **R3:** With the gate on, make-pr's base-detection cascade gains a parent-spec rung: when the spec has a flow dependency on a spec whose branch has an open PR, the default base resolves to that dependency's branch (an explicit base override still wins; no dependency means the existing cascade is unchanged). [paraphrase]
- **R4:** With the gate on and the resolved base being another open flow-authored PR's branch, make-pr links the new PR into a stack after create: extend the parent's existing stack via the add endpoint when one exists, else create a stack from parent + new PR. Implemented with plain `gh api` REST calls - the gh-stack extension is never required. [paraphrase]
- **R5:** Stack-link failure is non-fatal: on 404/409/422 (preview not enabled on the repo, concurrent modification, validation refusal) make-pr emits one stderr note and the PR stands as a plain dependent PR. Linking never blocks or fails PR creation. [paraphrase]
- **R6:** A linked PR's body records its stack membership in one line (stack number and position) sourced from the API response, consistent with the no-fabrication guardrails. [inferred]
- **R7:** Draft PRs join stacks correctly (verified live); draft/ready semantics for non-stacked PRs are untouched. [inferred]
- **R8:** Stacked layers default to READY, not draft: with the gate on, a stack-linked PR whose open-items count is zero is created ready - a human merging from the stack UI cannot merge drafts, and readiness is not merge consent (the human, or land when chosen, still gates the merge). Open items still force draft; an explicit draft flag always wins. This ready-default applies under Ralph/autonomous drivers too, as a documented gate-scoped exception to forced-draft (the human-review gate moves from "flip draft to ready" to "merge the layer"). [user]

## Boundaries

- No merge behavior changes in this spec - stacked merging and retarget tolerance are the land hardening spec's scope (fn-149). [paraphrase]
- No gh-stack extension dependency, no local stack-tracking files, no stack restructuring operations (reorder, fold, unstack). [user]
- No merge-queue integration. [inferred]
- No flowctl Python changes - this is skill-prose plumbing over gh, per the skill-plus-thin-plumbing doctrine. [paraphrase]
- Docs: make-pr skill reference and orchestration docs gain a short opt-in section; docs-site changelog entry under Unreleased. [inferred]

## Decision Context

Why REST over the gh-stack extension: `gh api` is already authenticated and required by the review/PR subsystem on every host; the extension adds an install step, a version surface, and local state files for zero gain at the linking layer (its value is the local branch-management UX, which users can adopt independently - our stacks are plain branches + PRs and fully interoperable with it). Verified live that stack creation from pre-existing plain PRs works, so make-pr's existing create path needs only a post-create link call. [paraphrase]

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

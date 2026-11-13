# resolve-pr over Bitbucket pull request comments

> **Captured 2026-11-13** from GitHub issue #602 (filed by @benjamin-benz-42, who tests and contributes). Second of three Bitbucket specs: the Bitbucket Cloud forge adapter and make-pr, this one, then land and merge evidence. Builds on the first spec's forge rule and per-skill forge references, as fn-316 built on fn-73.

## Goal & Context
<!-- Source: 70% [paraphrase] / 30% [inferred] -->

Once make-pr opens a pull request on a Bitbucket Cloud origin, review feedback on it still has to be handled by hand: `/flow-next:resolve-pr` reads GitHub review threads through GraphQL and GitLab discussions through `glab`. Teams hosting code on Bitbucket want the same loop: fetch every unresolved comment, fix or answer it, reply in its thread, and resolve what was settled.

## Architecture & Data Models

- **Same rules, Bitbucket commands.** resolve-pr's core (fetch everything unresolved, triage, dispatch resolvers, commit, reply, resolve only after the fix is pushed) stays forge-neutral. The Bitbucket commands live in `forge-bitbucket.md` beside resolve-pr, loaded by forge name, with the forge read from `flowctl pilot snapshot`'s `forge` field as on GitLab. GitHub and GitLab skill paths are not edited. [paraphrase]
- **Bitbucket comments are not review threads.** A Bitbucket PR comment is inline (file and line) or general, replies point at a parent comment, and a top-level comment carries its own resolution state. Replies go in the thread under the top-level comment. [paraphrase]
- **Agent-driven.** No new flowctl verb or adapter read: listing, replying and resolving are actions the agent performs through `bkt`. [paraphrase]

## API Contracts

- Record live before relying: list a PR's comments with their resolution state and parents (with pagination), reply under a comment, resolve a comment, and how a comment on an outdated diff position is reported. [inferred]

## Edge Cases & Constraints

- A comment is resolved only after its fix is pushed to the PR's source branch and verified, never on a local-only promise (same rule as GitHub and GitLab). [inferred]
- Comments on outdated diff positions are still fetched and handled. Bitbucket has no outdated flag and never moves a comment's line; when a push changes the line, it keeps the comment on the earlier head its code link names, while a comment on an unchanged line moves to the new head (measured 2026-11-13). That earlier head marks the comment outdated. [inferred]
- Deleted comments are skipped; Bitbucket keeps them in the listing with `deleted: true` and empty content (measured 2026-11-13). [inferred]
- Any top-level comment, inline or general, can be resolved; a resolved one carries a `resolution` key the others lack. Resolving it again answers `409 Conflict: Comment has already been resolved.`, which counts as already settled (measured 2026-11-13). [inferred]
- A reply names only its direct parent, and replies can nest; each is grouped under its top-level comment, and a reply whose parent is missing makes the listing unreadable. [inferred]
- Comment bodies are untrusted input: never executed. [inferred]
- `mode:autonomous` behaves as on GitHub: needs-human items become report lines and the run ends with `RESOLVE_PR_VERDICT=`. [inferred]

## Acceptance Criteria

- **R1:** On a Bitbucket origin, resolve-pr fetches every unresolved top-level comment, inline or general, with its replies, in one pass across all pages. [paraphrase] Errors: `bkt` missing or logged out, or a listing that cannot prove it is complete, stops resolve-pr with the reason; it never reports "nothing to resolve".
- **R2:** For each comment it fixes, resolve-pr replies in the thread citing the fix and resolves the comment only after the fix is pushed and verified; a comment it answers or declines with evidence gets that reply and is resolved, as on GitHub; one it cannot settle (`needs-human`) gets a reply and stays open. [inferred] Errors: a reply or resolve call that fails is reported and leaves the comment open.
- **R3:** The Bitbucket commands live in resolve-pr's `forge-bitbucket.md`, loaded by forge name; resolve-pr's GitHub and GitLab paths and their tests are unchanged. [paraphrase] Errors: no error surface beyond R1.
- **R4:** Each `bkt` command this spec relies on is first run against the live Bitbucket Cloud test workspace and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1–R2 in CI. [paraphrase] Errors: none beyond the fixtures being real output.

## Boundaries

- No land or merge here; that is the next spec. [paraphrase]
- No new public flowctl verb. [paraphrase]
- Bitbucket PR tasks (the checklist items reviewers attach to a PR) are not created, completed or resolved here. [inferred]
- Bitbucket Cloud only; no Data Center. [paraphrase]

## Strategy Alignment

- **Cross-platform parity** — the second step of the ship loop on Bitbucket Cloud. [strategy:Cross-platform parity]

## Decision Context

### Motivation
Review feedback is the second step of the ship loop. With make-pr working on Bitbucket, unresolved PR comments become the next manual step for Bitbucket teams.

### Implementation Tradeoffs
- **Reference file, not a flowctl adapter read.** Comment handling is agent action, not a deterministic decision, so it stays in skill prose per fn-73's "reads in flowctl, actions in skills" rule, as fn-316 did. [paraphrase]
- **Resolve rule follows GitHub (fn-316's amendment).** Every comment is resolved after its reply except `needs-human` ones, so projects that block merge on unresolved comments are not blocked by declined ones. [paraphrase]

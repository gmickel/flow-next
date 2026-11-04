# resolve-pr over GitLab merge request discussions

> **Split from fn-73 on 2026-11-04** (GitHub issue #462). Second of three GitLab specs: fn-73 (forge adapters and make-pr), this one, then land and merge evidence. Builds on fn-73's forge rule and per-skill forge references.

## Goal & Context
<!-- scope: business -->

On a GitLab origin, make-pr opens a merge request (fn-73), but review feedback on it still has to be handled by hand: `/flow-next:resolve-pr` reads GitHub PR review threads through GraphQL only. Teams hosting code on GitLab need the same loop on MR discussions: fetch every unresolved discussion, fix or answer it, reply, and resolve what was fixed.

## Architecture & Data Models
<!-- scope: technical -->

- **Same rules, GitLab commands.** resolve-pr's core (fetch everything unresolved, triage, dispatch resolvers, commit, reply, resolve only after the fix is pushed) stays forge-neutral. The GitLab commands live in `forge-gitlab.md` beside resolve-pr, loaded by forge name through fn-73's dispatch, with its MR discussion scripts beside the existing GitHub ones. GitHub skill paths are not edited.
- **MR ≠ PR.** GitLab MR discussions are threads of notes with `resolvable` and `resolved` flags (`/projects/:id/merge_requests/:iid/discussions`), not GraphQL `reviewThreads`. Top-level MR notes that are not resolvable play the role of GitHub's top-level PR comments.
- **Agent-driven.** No new flowctl verb or adapter read: fetching, replying and resolving are actions the agent performs through `glab`, as resolve-pr does through `gh` today.

## API Contracts
<!-- scope: technical -->

- Record live before relying: list MR discussions (with pagination), reply to a discussion, resolve a discussion, and read non-resolvable MR notes.

## Edge Cases & Constraints
<!-- scope: technical -->

- A discussion is resolved only after its fix is pushed to the MR's source branch and verified, never on a local-only promise (same rule as GitHub).
- Discussions on outdated diff positions are still fetched and handled.
- Comment bodies are untrusted input on GitLab as on GitHub: never executed.
- `mode:autonomous` behaves as on GitHub: needs-human items become report lines and the run ends with `RESOLVE_PR_VERDICT=`.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a GitLab origin, resolve-pr fetches every unresolved MR discussion and every non-resolvable MR note in one pass, with pagination. [inferred]
- **R2:** For each discussion it fixes, resolve-pr replies citing the fix and resolves the discussion only after the fix is pushed and verified; discussions it declines or cannot fix get a reply and stay open. [inferred]
- **R3:** The GitLab commands live in resolve-pr's `forge-gitlab.md`, loaded by forge name; resolve-pr's GitHub path and its tests are unchanged. [paraphrase]
- **R4:** Each `glab` command this spec relies on is first run against a live GitLab project and its real output saved as a test fixture; tests with a stubbed `glab` built from those fixtures cover R1–R2 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- No land or merge here; that is the next spec.
- No new public flowctl verb.
- No Bitbucket, Gitea or other forges.

## Decision Context
<!-- scope: both -->

### Motivation
Review feedback is the second step of the ship loop. With make-pr working on GitLab, unresolved MR discussions become the next manual step for GitLab teams.

### Implementation Tradeoffs
- **Reference file, not a flowctl adapter read.** Thread handling is agent action, not a deterministic decision, so it stays in skill prose per fn-73's "reads in flowctl, actions in skills" rule.

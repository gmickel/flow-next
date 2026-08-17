# Issue sweep: pilot worktree/reused-branch rules + tracker wire list-states

## Goal & Context
<!-- scope: business -->

Three valid field reports from @sn-furali (GitHub issues #354, #355, #356), all verified byte-for-byte against 4.0.0 source during triage:

- **#354**: Pilot's branch matrix hard-requires `git checkout` of the default branch for the `plan` / `plan-review` stages. Git allows a branch in exactly one worktree, so any secondary worktree (the Worktree Kit's own one-worktree-per-spec guidance) fails that checkout and every tick dies `NEEDS_HUMAN` before dispatch. Two shipped flow-next practices cannot be composed. The rule's stated rationale is narrower than the rule: the property that must hold is "never write planning state onto a branch with an open PR".
- **#355**: Pilot's all-done classification says "MERGED PR exists while the spec is still open: NEEDS_HUMAN". That holds only for one-PR-per-branch shapes. A team opening one PR per gate (capture, plan, plan-review, then work) legitimately arrives at make-pr with several MERGED PRs, zero OPEN, and unshipped work commits. make-pr's own Forbidden list states the opposite rule ("Closed/merged PRs on a reused branch must NOT trigger refusal"), so the toolchain contradicts itself.
- **#356**: No read-only way to ask a tracker which workflow states exist. The only state-resolving command, `tracker resolve`, WRITES `.flow/config.json` (and in one observed case moved a hand-selected `stateIds.done` off the team's chosen state). Consumers cannot answer "does every configured state id still name a live state?" without building a second tracker client, which the transport layer exists to prevent. The internal queries already exist (Linear `workflowStates` with `hasNextPage` guard, Jira project statuses) behind resolve; only the read-only surface is missing.

All three fit strategy: pilot correctness for autonomous loops, and tracker transport completeness (deterministic flowctl plumbing per the agentic/deterministic split).

## Architecture & Data Models
<!-- scope: technical -->

Two independent workstreams:

1. **Pilot prose fixes** (skill workflow only, no Python): edit `flow-next-pilot` workflow Phase 3 branch matrix and the all-done classification rule. Codex mirror regenerated via sync script. Conduct checklist for pilot applies at review.
2. **`tracker wire list-states`** (deterministic flowctl Python): new context-free wire verb (like `list-open` / `attach-get`, no locator) in the tracker wire package. Reuses the existing per-provider state fetch paths (Linear GraphQL `workflowStates` including pagination signal; Jira `/project/<key>/statuses`). Same locator/transport/envelope conventions as existing wire verbs. Providers with no workflow-state pool (GitHub, GitLab: their mapping model is labels + open/closed, no state ids exist in `tracker.resolved`) return a typed unsupported error rather than inventing a projection. Tracker manifest regenerated (`gen_tracker_manifest.py`).

## API Contracts
<!-- scope: technical -->

`flowctl tracker wire list-states [--json]`

Success JSON (shape is exhaustive):

```json
{"states": [{"id": "…", "name": "…", "type": "…"}], "complete": true}
```

- `type`: Linear workflow-state `type` (`backlog|unstarted|started|completed|canceled`); Jira `statusCategory` key.
- `complete`: the load-bearing completeness signal. `true` only when the provider listing is provably exhaustive (Linear: `hasNextPage == false`; Jira: the statuses endpoint is unpaginated, so a well-formed response is complete). When the underlying listing is truncated, return the partial `states` with `complete: false` and exit 0; the caller decides to refuse.
- Read-only invariant: no code path of this verb writes `.flow/config.json` (or any `.flow/` file).
- Errors (typed TrackerError envelope, same classes as other wire verbs): GitHub/GitLab destination: unsupported (message states these trackers have no workflow-state pool); unresolved/missing destination (`teamId` / `projectKey`): unresolved; malformed provider response or transport failure: transport. Non-JSON mode prints the human rendering like other wire verbs.

### Pilot rule contracts (prose, exact behavior)

Branch matrix row for `plan` / `plan-review` (replaces the unconditional default-branch checkout):

- Probe the current branch for an OPEN PR (`gh pr list --head <branch> --state open`). No open PR (including a fresh worktree branch or the default branch itself): stay on the current branch and dispatch. Open PR exists: check out the default branch; if that checkout fails (e.g. a worktree already holds it), `NEEDS_HUMAN` naming the branch and the reason. Probe failure (gh unavailable/error): attempt the default-branch checkout as before; if it fails, `NEEDS_HUMAN` (fail-safe: never plan onto a possibly-PR-carrying branch on an unknown probe).
- The multi-spec-loop rationale sentence is updated to state the property (never write planning state onto a branch with an open PR), not the mechanism.

All-done classification (replaces the unconditional MERGED rule):

- MERGED PR(s) exist, spec still open, no OPEN PR: head-identity check - refuse only when the newest merged PR's `headRefOid` equals the current branch head (implementation note, review round 1: the originally drafted `git rev-list --count <default-base>..<branch-head>` alternative is WRONG under squash-merge - land squash-merges, so ancestry counts read fully-shipped work as unshipped; head identity is the shipped rule). Heads differ: NOT an inconsistency; classify the spec as make-pr-eligible and proceed. Heads equal: keep `NEEDS_HUMAN` (a merged PR with nothing new and an open spec is the genuinely inconsistent state). Empty `headRefOid` / rev-parse failure: keep `NEEDS_HUMAN`, unchanged from today.

## Edge Cases & Constraints
<!-- scope: technical -->

- `list-states` with `tracker.resolved` absent or destination unresolved: typed unresolved error, no partial output.
- Linear >100 states: first page returned with `complete: false` (single-query shape mirrors the existing internal readiness query); do not add cursor-drain machinery unless it already exists for reuse.
- G2 applies to all new tests: assert behavior/contract (JSON fields, error classes, the no-write invariant), never prose.
- G1 applies to the pilot prose edits: the replacement rules must not grow the always-loaded surface beyond what the fix buys; prefer replacing sentences over adding paragraphs.
- Prompt-text pin: if `test_prompt_text_pinned.py` pins the pilot workflow, update hashes in the same commit with rationale (deliberate prompt change: issues #354/#355).
- flowctl.py / flowctl_tracker changes require: `gen_tracker_manifest.py` regen + `sync-codex.sh` twice (idempotent) at the final gate, plus the SOURCE_SHA256 pin refresh if flowctl.py itself changes.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Pilot's `plan` / `plan-review` stages are runnable from a secondary git worktree: the branch matrix stays on the current branch when it has no open PR, checks out the default branch only when the current branch has an open PR, and reports `NEEDS_HUMAN` (naming branch + reason) only when that fallback checkout fails. Errors: open-PR probe failure degrades to the default-branch-checkout attempt, then `NEEDS_HUMAN` on its failure (fail-safe, never plan onto an unknown-status branch).
- **R2:** Pilot's all-done classification treats merged gate PRs on a reused branch with unshipped commits as make-pr-eligible, not `NEEDS_HUMAN`; the `NEEDS_HUMAN` verdict is retained exactly when the branch head equals the newest merged PR head (head identity, never ancestry - squash-merge-safe). Errors: missing `headRefOid` / rev-parse failure keeps today's `NEEDS_HUMAN`.
- **R3:** `flowctl tracker wire list-states [--json]` exists as a read-only context-free wire verb for Linear and Jira, returning the exhaustive shape `{"states": [{"id","name","type"}], "complete": bool}` with `complete` provably distinguishing a full listing from a truncated one. Errors: GitHub/GitLab: typed unsupported; unresolved destination: typed unresolved; malformed/transport failures: typed transport; truncated listing: partial `states` + `complete: false`, exit 0.
- **R4:** No `list-states` code path writes `.flow/config.json` or any other `.flow/` file, asserted by test across success, truncated, and error outcomes.
- **R5:** Docs and changelogs land in the same workstream: `flowctl.md` wire-verb table + CLI listing, `tracker-sync.md` wire section, repo `CHANGELOG.md` `## Unreleased` entries crediting @sn-furali (#354, #355, #356), and a docs-site changelog Unreleased entry staged per the customer-register rules. No version bump (batched releases). Errors: no error surface beyond the standing docs gates.

## Boundaries
<!-- scope: business -->

- No `setup-version set` verb (#314 stays parked on fn-160) and no Ralph scope isolation (#89 stays parked on fn-61).
- No `list-states` for GitHub/GitLab beyond the typed unsupported error; no label-enumeration analogue.
- No pagination/cursor drain machinery for Linear states beyond the single-page + completeness signal.
- No changes to `tracker resolve` semantics; it keeps its write behavior. The verb is detection, resolve stays repair.
- No stateIds liveness *checker* (the "does every configured id still exist" comparison stays in the consumer; flow-next ships the read primitive only).
- No release/version bump in this spec.

## Decision Context
<!-- scope: both -->

Single spec for a three-issue sweep because the pilot fixes are two rules in one file and the verb is thin plumbing over existing provider queries; separate specs would triple ceremony for one review surface. Property-based pilot rules (open-PR probe, unshipped-commit count) over worktree special-casing: the reporters' suggested discriminators match capabilities pilot already uses elsewhere (`gh pr list --head`, rev-list), so no new machinery. `list-states` scoped to Linear + Jira because only those providers have a workflow-state pool with ids in `tracker.resolved`; a GitHub/GitLab projection would invent semantics the mapping model does not have. Truncation returns `complete: false` rather than an error because the issue's requirement is that callers can refuse, not that flowctl decides for them.

## Quick commands

- Task 1 (pilot prose): `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_pilot_strikes_prose -q` then `./scripts/sync-codex.sh` twice (idempotency).
- Task 2 (list-states): `cd plugins/flow-next/tests && python3 -m unittest test_tracker_wire test_tracker_conformance test_tracker_distribution -q`; `python3 scripts/gen_tracker_manifest.py`.
- Task 3 (docs): full gate applies (docs pins live in the unit suite).
- Final gate, once: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + `python3 scripts/gen_tracker_manifest.py` + `./scripts/sync-codex.sh` twice.

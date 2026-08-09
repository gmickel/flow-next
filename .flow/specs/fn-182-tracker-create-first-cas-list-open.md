# Overview

Three tracker-bridge gaps plus one documentation seam, from issues #310, #311, #315, #309 (sn-furali 2026-08-08 batch): the create-first mint claim is an atomic write rather than compare-and-set so a promotion race leaves two specs for one candidate; `wire list-open` returns a silent confidently-wrong empty when `tracker.readyState` is unset (confirmed live against a populated board); the Linear provider cannot place an issue in a Project; and the abandon path for a never-promoted candidate is undocumented.

**Evidence standing: reporter-verified at 3.16.3 with quoted source and one live-bridge observation; `providers/linear.py` contains `project` zero times, confirmed. No new evals.**

## Goal & Context

Close the concurrency hole with a conditional write, turn the silent-empty into a handleable error, carry a per-spec Linear Project id through the existing projection, and write down the candidate-abandon contract. All four are the minimum shape the issues themselves prefer.

## Architecture & Data Models

1. **CAS mint claim (#310):** `sync create-first-put` gains `--if-absent` (succeed only when the record's `specId` is absent) and optionally `--expect-spec-id <id>`; the loser of a promotion race gets a distinct CONFLICT error instead of overwriting the winner. Runs under the config lock already held. Pending-claim design untouched.
2. **list-open capability error (#311, minimum fix):** when `readyState` is unset for Linear, `wire list-open` returns an explicit unresolved/capability error instead of `{"issues": [], "truncated": false, "success": true}`. A caller can handle a refusal; it cannot detect a silent empty. Independent-of-readyState enumeration is NOT in scope (see Boundaries).
3. **Per-spec Linear Project (#315, option 1 only):** spec sidecar fields `tracker.projectId` / `tracker.projectMilestoneId`, sent on `issueCreate` and reconciled on `issueUpdate` by the Linear provider. flow-next carries the id it is given; it never creates or manages Projects. The generic payload-extension seam (issue's option 2) is declined as extensibility sprawl; the narrow field matches how membership actually varies (per spec, not per repo).
4. **Abandon-path docs (#309):** tracker-sync.md documents the intended shape for a never-promoted candidate: close/cancel the remote issue first (ownership: the consumer's, in the tracker UI or via the tracker's own tooling), then `create-first-clear`; ordering stated so a live intake issue is never left with no local trace. One paragraph, no new verb.

## Edge Cases & Constraints

- #310: the stale-claim reclaim window (crash between remote create and record write) is acknowledged in the code's own comment and stays out of scope; this spec fixes the spec-mint race only.
- #311: leaving `readyState` unset is a legitimate, deliberate configuration (projection armed = governance token); the error message must say what is unresolved and how to resolve it, not tell the user to arm the projection.
- #315: fields are optional; absent fields produce today's payload byte-identically. Reconcile must not clear a Project set tracker-side when the sidecar field is absent (absent = unmanaged, not none). New config/sidecar keys go through the fn-138 schema TABLE + drift test if any land in config.json (sidecar fields do not).
- #309 docs answer must state clearly which side owns the remote close, per the issue's ordering/ownership question.
- Linear GraphQL: `IssueCreateInput`/`IssueUpdateInput` already accept `projectId`/`projectMilestoneId`; no API upgrade needed. Smoke against the flow-next-smoke Linear sandbox where practical.

## Acceptance Criteria

- **R1:** `create-first-put --if-absent` fails with a distinct CONFLICT when `specId` is already set; without the flag, behavior is unchanged. The #310 two-promoter race ends with exactly one recorded spec and one informed loser.
- **R2:** Linear `wire list-open` with unset `readyState` returns an explicit error envelope naming the unresolved configuration; with `readyState` set, behavior unchanged. Errors: this IS the error path; no silent empty remains.
- **R3:** A spec with sidecar `tracker.projectId` (and optional `projectMilestoneId`) produces an `issueCreate` carrying those fields and an `issueUpdate` reconciling them; a spec without them produces today's payload. Errors: an invalid project id surfaces the provider error, never a silent drop.
- **R4:** Reconcile never clears tracker-side Project membership when the sidecar field is absent.
- **R5:** tracker-sync.md documents the never-promoted-candidate abandon path with explicit ordering and ownership; #309 is answerable by link.
- **R6:** Mirrors, dual copies, tracker manifest regen, docs, CHANGELOG Unreleased crediting @sn-furali. Errors: parity red blocks merge.

## Boundaries

- No independent-of-readyState enumeration verb and no remote-lookup create-first-get (#311 options 1 and 3 deferred; the capability error is most of the value at a fraction of the surface).
- No generic issue-payload extension seam (#315 option 2 declined).
- No Project creation/lifecycle management, no Triage Rules, no change to `CAPABILITIES["subIssues"]`.
- No change to the pending-claim design or the git-local recovery record (#310/#311 explicitly do not ask).
- No distributed lock. Version bump deferred to the batched release.

## Decision Context

Scope choices follow the issues' own preference orderings except #311, where the minimum option (2: explicit error) is taken over the preferred option (1: independent enumeration) - an enumeration verb decoupled from readyState is new query surface with its own pagination/truncation contract, while the error closes the actual trap (a dedup query that looks healthy and is blind) immediately; option 1 can be a follow-up if a real consumer materializes. #315 option 1 over option 2 is the anti-config-sprawl call: a named field flow-next understands beats an open payload seam that outsources semantics to every integrator. That rejection is recorded in the declined ledger at `.flow/memory/declined/tracker-issue-payload-extension-seam.md` (2026-08-09).

# Unready a tracker issue and link named issues in any id mode

## Goal & Context

<!-- Source: 0% user / 40% [paraphrase] / 60% [inferred] -->

Two tracker pieces that an unattended start from a tracker issue needs (the sibling spec, "Unattended start from a tracker issue: flow --from-issue", depends on this one). Both are useful on their own. [paraphrase]

- **Moving an issue out of the ready state.** When an issue in `tracker.readyState` is not clear enough to build, the run asks its questions on the issue and moves it out of the ready state, so the board shows it is waiting on a person and a person's later move back to the ready state re-triggers it. Today flowctl can move a tracker issue only through the status verb, which needs a linked spec, and a refused issue has no spec. On Linear and Jira an agent has no other way to change an issue's state without calling the provider API with credentials. [inferred]
- **Linking a named issue in the default id mode.** In flow-id mode (`tracker.specIds` unset or `flow`), a capture that names an existing tracker issue never records it as the spec's tracker link, so with the capture push on, the spec gets a second, new issue. This was fn-314's R1 and moves here. [paraphrase]

## Architecture & Data Models

- **`tracker wire unready`** moves one issue, named by locator, out of the ready state. It is provider-neutral: the caller never branches on tracker type. [inferred]
  - Linear and Jira: move the issue to the normalized `backlog` slot already resolved in the tracker config. [paraphrase]
  - GitHub and GitLab: remove the `tracker.readyState` label, which is how readiness is expressed there. [inferred]
  - It needs no linked spec and writes no spec state. [inferred]
- **Capture links a named issue in every id mode.** When the request names an existing issue and the bridge is active, capture records that issue as the spec's tracker link in flow-id mode too, through the existing link plumbing, so the capture push updates that issue instead of creating one. Tracker-id mode keeps today's tracker-first mint. [paraphrase]

## API Contracts

- `flowctl tracker wire unready --locator <issue> --json` returns the existing wire envelope with the issue's state before and after: [inferred]

```json
{"success": true, "issue": {"id": "<durable id>", "identifier": "SCF-12"}, "from": "Todo", "to": "Backlog", "changed": true}
```

- An issue already out of the ready state returns `changed: false` and makes no write. [inferred]

## Edge Cases & Constraints

- **No `backlog` slot** (allowed on Jira, where many workflows lack one): a typed error naming the missing slot; no state is changed. [inferred]
- **`tracker.readyState` unset or the bridge inactive:** a typed error; nothing is called. [inferred]
- **The named issue cannot be read during capture:** capture reports it and saves the spec unlinked, as it handles an unknown issue today. [paraphrase]
- **The issue is already linked to another spec:** the existing one-issue-one-spec collision rule refuses the link and capture reports which spec holds it. [inferred]

## Acceptance Criteria

- **R1:** `tracker wire unready` moves an issue in the ready state to the `backlog` slot on Linear and Jira, and removes the `tracker.readyState` label on GitHub and GitLab, returning the envelope above with `changed: true`. Errors: issue already out of the ready state → `changed: false`, no write; no `backlog` slot → typed error, no change; `readyState` unset or bridge inactive → typed error, no call; unreachable transport or unknown issue → the existing wire error envelope. [inferred]
- **R2:** In flow-id mode with an active bridge, a capture that names an existing issue records that issue as the spec's tracker link; a capture push afterwards updates that issue and creates no second one. Errors: the issue cannot be read → capture reports it and saves the spec unlinked; the issue is linked to another spec → the link is refused and capture names that spec. [paraphrase]
- **R3:** Tracker-id mode capture and every other `tracker wire` verb behave as in 9.10.0. No error surface beyond R1 and R2. [inferred]

Tests cover R1 with fake transports for all four providers, including the no-change and no-backlog cases, and R2 in flow-id mode on at least one provider; the existing tracker and capture suites pass. [inferred]

## Boundaries

- No move to any state other than `backlog`, and no configurable target state. [inferred]
- No issue-to-spec matching in flowctl. [inferred]
- No change to the status verb or to lifecycle status pushes. [inferred]

## Decision Context

- **One provider-neutral verb, not label calls plus a state call.** GitHub and GitLab could already drop the label through `tracker wire label`, but the caller would then branch on tracker type, which the tracker bridge keeps out of skills. The unattended failure it prevents: a refused issue left in the ready state, so the board says "ready" while it waits on a person, and on Linear or Jira the run has no other credential-safe way to move it. [inferred]
- **`backlog` as the target.** Gordon chose the canonical backlog state over a dedicated "needs input" state: it needs no new configuration. [paraphrase]
- **The link fix moved from fn-314.** The issue start needs it, and fn-314's attended triage is not needed for it; Gordon chose to move it here, and fn-314 now depends on this spec. [paraphrase]

## Strategy Alignment

- Tracker determinism: a zero-judgment tracker mutation moves into the deterministic tracker package instead of skill prose or ad hoc API calls. [strategy:Tracker determinism]

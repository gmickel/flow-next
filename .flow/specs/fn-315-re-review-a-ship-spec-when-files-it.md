# Re-review a SHIP spec when files it cites changed before work starts

## Goal & Context

GitHub issue #505. A spec can pass plan-review and then wait days or weeks before anyone builds it. Meanwhile other specs merge and the files it describes change. Nothing notices. A plan review goes stale only when the spec's own text changes, and the time it was reviewed is never compared with anything. [paraphrase]

Each plan-review verdict already stores the commit it reviewed. When a spec was reviewed SHIP and no task has started, flow can check whether any file the spec cites has changed since that commit. If one has, flow sends the spec back to the existing plan-review route before building it. The reviewer still makes the call; the check only decides that a review is due. [inferred]

The unattended failure this prevents: `flow --auto` and goal mode build a spec on a SHIP verdict whose premises moved since the review, with no one looking. [inferred]

## Architecture & Data Models

- **Drift is derived on read; nothing is stored.** The check runs only when all of these hold:
  - the spec's plan-review status is `ship`;
  - the latest plan-review record carries the reviewed commit;
  - every task is still `todo`, or the spec has none.

  It then lists the repo paths the spec body cites in backticks (tokens containing a `/`), leaving out `.flow/`, and asks git which of them changed between the reviewed commit and HEAD. A non-empty list is drift. [inferred]
- **The route judge treats drift like a stale review.** It routes to `plan_review`, with the reason naming the changed files. The pilot snapshot sees the same thing, so `flow --auto` and goal mode re-review before work. [inferred]
- **A new SHIP clears it.** The next SHIP records a newer commit, and the check then finds nothing. There's no flag to reset and no config key. [inferred]
- **Direct `/flow-next:work` warns.** When it's run on a spec with drift, it prints one line naming the changed files and continues. Flow's routing is the path that acts on drift. [inferred]

## API Contracts

- The route decision for a drifted spec is the existing `plan_review` route, with a reason of this shape: [inferred]

```text
plan review predates changes to cited files: <path>, <path>
```

- `flowctl show <spec> --json` gains `plan_review_drift`: the list of changed cited paths. It's empty when there's no drift or the check doesn't apply. [inferred]

## Edge Cases & Constraints

- **The reviewed commit is missing or unreachable** (an older record, a rebase, a shallow clone): there's no drift, and today's rules apply. [inferred]
- **The spec cites no paths:** there's no drift. About half the specs in this repo cite no full path, so this check catches only part of #505's case. [inferred]
- **Backtick tokens that aren't paths** match nothing and are ignored. A cited file deleted since the review counts as changed. [inferred]
- **Any task is `in_progress` or `done`:** no check runs. The work has started, and plan-sync and review cover it from there. [inferred]
- **Cost:** one `git diff --name-only` per route call, only for specs that meet the conditions above. No model call is made unless drift sends the spec to plan-review. [inferred]

## Acceptance Criteria

- **R1:** For a spec reviewed SHIP with all tasks `todo`, a commit after the reviewed one that changes a backtick-cited path makes the route judge return `plan_review`, with the changed path in the reason. Errors: a missing or unreachable reviewed commit → no drift, and the route is unchanged. [inferred]
- **R2:** A commit that changes only uncited files, or only files under `.flow/`, leaves the route unchanged. [inferred]
- **R3:** After a new SHIP plan review at the current HEAD, the same spec routes as it did before the drift. [inferred]
- **R4:** With any task `in_progress` or `done`, or with a plan-review status other than `ship`, the route is exactly what it is today. [inferred]
- **R5:** `pilot snapshot` reports the same `plan_review` decision for a drifted spec as the route judge. [inferred]
- **R6:** `flowctl show <spec> --json` carries `plan_review_drift` (the changed cited paths, or empty). Direct `/flow-next:work` on a drifted spec prints one line naming them and continues. [inferred]
- **R7:** Tests cover R1-R6 against fixture git repos: a cited change, an uncited change, a `.flow/`-only change, a deleted cited file, a re-SHIP, a started task, a missing commit, and the pilot parity. The full existing route, pilot and work suites pass unchanged. [inferred]

## Boundaries

- No configured command hook before plan or work (the issue's option 1). [inferred]
- No flow-next version comparison. [inferred]
- No age, commit-count or time-based trigger. [inferred]
- No configured design-doc paths. Only what the spec itself cites counts. [inferred]
- No persisted stale flip. Drift is derived on read. [inferred]
- No bare-filename matching across the repo. [inferred]

## Decision Context

- **A trigger, not a verdict.** STRATEGY.md bans deterministic stand-ins for judgment. Here the diff only decides that a review is due, the plan reviewer judges, and the check is the same kind of fact as the existing "spec text changed → stale" rule. [inferred]
- **Partial coverage is accepted.** A design doc reassigning scope is invisible unless the spec cites it. The check is cheap and catches the case where it applies. [inferred]
- **Command hook rejected.** It would be a new key that does nothing unless configured, and projects would each reinvent the same check. [inferred]
- **Version, age and commit-count checks rejected.** They're noisy, and they resemble the trend heuristics the wall-clock research already rejected. [inferred]

## Strategy Alignment

- Autonomous mode: unattended runs stop building on a review whose premises moved. [strategy:Autonomous mode]

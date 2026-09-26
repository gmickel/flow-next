# Chart subjects

Read this only when the tracker subject is a chart or decision. Chart
projection reuses the lifecycle facade with subject kind `chart` / `decision`
([adapter-interface.md](adapter-interface.md) § Lifecycle verbs).

Optional when `tracker.charts` is the literal `on` and the bridge is active.
`.flow/charts/` remains canonical; remote state is an idempotent projection.

## Parent / child locator

| Subject | Kind | Locator storage | Remote shape |
|---|---|---|---|
| Chart | `chart` | chart JSON `tracker.{id,identifier,url}` | Parent issue |
| Decision | `decision` | decision JSON `tracker.{id,identifier,url}` | Child issue |

Locators are never chart identity. Durable id is the dedup and stale-parent
key across **all** subject kinds (specs, charts, decisions). Retry after
remote create but before local ledger publication completes the same identity
via the event marker + revision key.

## Hierarchy capability

| Capability | Lossless form | Degraded form |
|---|---|---|
| `subIssues` true (GitHub) | Native parent/child (`sub_issues`): chart = parent, decision = child | n/a |
| `subIssues` false (Linear, GitLab, Jira) | n/a | Labelled/linked flat issues; result reports `degraded.capability=subIssues`, `form=flat_linked` |

## Blocking projection

| Local edge | Remote projection |
|---|---|
| `blocked_by[]` | Native blocking relation **only** when `blockedBy` capability is true (Linear, Jira; GitLab when plan-gated probe says so). |
| `depends_on[]` | **Never** projected as an indistinguishable blocking edge. Local provenance only unless a future lossless distinct relation exists. Result stays silent on depends_on remote edges. |
| GitHub | No blocked-by; hierarchy is not a substitute for blocking. `blocked_by` stays local + owned body text; `degraded.capability=blockedBy`. |

## Decision child fields (lossless vs owned body)

Project through native fields/labels when lossless; otherwise an owned body
block (`<!-- flow-next:decision -->` ... `<!-- /flow-next:decision -->`) with
explicit degradation:

- D-ID, title, type, attendance, local status
- Safe resolution gist (never full answer bodies)
- Approved evidence references only (repo-relative paths, branch/commit refs,
  approved HTTPS URLs)
- Claim/release may refresh the owned block/counts; **never** maps to provider
  workflow status

Never copy: full answers, unsafe assets, credentials, acceptance-criterion
source tags.

## Parent rollup (compact only)

Owned block `<!-- flow-next:chart-rollup -->` ... carries:

- Chart Outcome and status
- Counts: actionable, blocked, claimed, resolved, superseded, out-of-scope, parked
- Latest resolved D-ID / title / safe gist
- Current frontier summary

## Lifecycle events (local-first, receipt-backed)

Each committed local revision produces one idempotent event marker + one
aggregate receipt. Events: `chart.create`, `chart.wire`, `chart.claim`,
`chart.release`, `chart.resolve`, `chart.supersede`, `chart.outOfScope`,
`chart.briefing`, `chart.abandon`, `chart.reopen`, `chart.staleLink`.

Partial / failed / reordered / unsupported remote steps persist completed
steps + receipt + revision so retry/reconcile converges without duplicate
issues/comments/relations and never rolls back local chart state.

## Locator re-entry (`flowctl chart locate`)

Resolves canonical chart/D-ID, stored identifier, or stored supported provider
URL **strictly** through the local provenance ledger:

- Normalize scheme/host case and provider-approved cosmetic suffixes
- Reject credential-bearing, wrong-host/project, ambiguous, unrecorded,
  stale-parent, and conflicting selectors
- Structured failures with codes such as `unresolved_locator`, `stale_id`,
  `unsupported_capability`; **zero mutation**
- No network search, no redirect following, no title inference
- Parent URL -> chart; open decision URL -> that D-ID; resolved/superseded
  decision URL -> history + replacement/frontier metadata (never silently
  different work)

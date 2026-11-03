# Intake for open tracker issues that no spec covers

## Goal & Context

GitHub issue #579. A team with an existing tracker backlog wants flow to look at the open issues that have no spec yet and propose what to do with each: capture a new spec, fold it into an existing spec, add it as a dependency, or leave it. Today flow reads one named issue at a time, and nothing walks the open issues. [paraphrase]

Today's gaps:

- `flowctl tracker wire list-open` only returns the ready lane. It's empty when `tracker.readyState` is unset, and on Linear it refuses.
- Backlog mode decides "which open issues have no spec" in prose. [inferred]
- Every row carries the provider's full `raw` payload, about 9 KB an issue on this repo, so 80 issues come to roughly 180K tokens. [inferred]

A real bug in capture blocks this. In the default flow-id mode (`tracker.specIds` unset or `flow`), a capture that names an existing issue never links the spec to it. When the capture push is on, the unlinked spec then gets a second, new issue. [inferred]

## Architecture & Data Models

- **Capture links a named issue in every id mode.** When the request names an existing tracker issue and the bridge is active, capture records that issue as the spec's tracker link in the default flow-id mode too, not only under `tracker.specIds: tracker`. The capture push then updates that issue instead of creating one. [inferred]
- **`wire list-open` gains two flags.** Both are plain deterministic plumbing that backlog mode already does in prose. [inferred]
  - `--any-lane`: every open issue in the configured destination, whatever the ready lane. It works on every provider with `tracker.readyState` unset.
  - `--unlinked`: drops issues already linked to a spec in this checkout. The check reads local sync state only and makes no tracker call.
  - With either flag, rows are compact: no `raw`, and the body cut to an excerpt.
- **Backlog mode reads `--unlinked`.** Its "tracker-only issues" step uses `list-open --unlinked` instead of the prose comparison, so the link logic lives in one place. [inferred]
- **One attended route.** Flow's route matrix gains one row: "triage the open issues" → read a short intake reference. That reference shows one table: each unlinked issue with one proposed action and a one-line reason. It asks the person for a single confirming pick, then runs the existing stages for what was picked. No new skill. [inferred]
  - **New spec:** capture, naming the issue, so the spec links to it.
  - **Fold into a spec:** amend that spec's body, push it, and comment on the issue pointing at the spec.
  - **Dependency:** capture the new spec and add a spec-level dependency (`spec add-dep`) on or from the existing spec.
  - **Leave:** do nothing.
- **Matching is the agent's judgment.** Which spec an issue belongs to is decided by the host reading titles and excerpts, never by flowctl. [inferred]

## API Contracts

- `flowctl tracker wire list-open [--any-lane] [--unlinked] --json`. Without flags, output is exactly as today. With either flag, each row is: [inferred]

```json
{"id": "<durable id>", "identifier": "#42", "title": "...", "url": "https://...", "labels": ["bug"], "excerpt": "<first 500 characters of the body>"}
```

- The envelope keeps `issues` and `truncated` as today. [inferred]
- `--unlinked` matches on the stored tracker id of every spec in `.flow/` in this checkout. [inferred]

## Edge Cases & Constraints

- **Attended only.** Under an autonomy marker, flow's existing attended refusal stops the route before any read. [inferred]
- **Unreachable tracker or bridge off:** the route reports why and stops, with no partial table. [inferred]
- **`truncated: true`:** the table says the list was cut and shows how many issues it covers. [inferred]
- **Folded issues reappear on later runs.** They have no link of their own, so the host proposes "covered by fn-N, leave" for them. No ignore list or label exclusion is added. [inferred]
- **Issues linked only from a spec on another branch** count as unlinked. Capture's existing duplicate scan, which reads branch-only specs, catches a repeat capture. [inferred]
- **Empty result:** the route says there's nothing to triage and stops. [inferred]

## Acceptance Criteria

- **R1:** In flow-id mode with an active bridge, a capture that names an existing issue records that issue as the spec's tracker link. A capture push afterwards updates that issue, and no second issue is created. Errors: the named issue can't be read → capture reports it and saves the spec unlinked, as an unknown issue is handled today. [inferred]
- **R2:** `wire list-open --any-lane` returns every open issue in the destination on GitHub, GitLab, Linear and Jira with `tracker.readyState` unset, in the compact row shape above. Errors: unreachable transport → the existing error envelope; a page cap → `truncated: true`. [inferred]
- **R3:** `wire list-open --unlinked` omits every issue whose id is stored as a spec's tracker link in this checkout and makes no extra tracker call for that check. Combined with `--any-lane`, it covers all lanes; alone, the ready lane. Errors: no error surface beyond R2's. [inferred]
- **R4:** `wire list-open` without the new flags returns the same output as 9.5.1. [inferred]
- **R5:** Backlog mode's tracker-only set comes from `list-open --unlinked`, and its candidate set on a fixture backlog is unchanged. [inferred]
- **R6:** Attended flow, given "triage the open issues", shows one table of unlinked issues with one proposed action and a reason each. It asks one confirming question, then runs only the existing stages for the picked actions. Errors: an autonomy marker → the existing attended refusal; tracker unreachable → stop with the reason. [inferred]
- **R7:** Tests cover R1-R5 with fake transports for every provider. That includes the flag combinations, the unchanged default output, the no-API-call link check, and capture linking in flow-id mode. R6 gets a prose-contract test that pins the route row and the reference's one-table, one-question shape. The full existing tracker and flow suites pass. [inferred]

## Boundaries

- No unattended intake; backlog mode already covers the ready lane unattended. [inferred]
- No ignore list or "seen" ledger, and no label written to exclude folded issues. [inferred]
- Folded issues are not closed or relabelled. [inferred]
- No issue-to-spec matching in flowctl. [inferred]
- No new skill or command. [inferred]
- No task-level `dep add` from an issue; dependencies are spec-level. [inferred]

## Decision Context

- **Two flags on an existing verb, not a new verb.** The link check and the any-lane listing are zero-judgment facts that backlog mode already works out in prose. Moving them into flowctl meets the burden-of-proof rule, since there are two consumers. [inferred]
- **Compact rows only under the new flags.** Callers of today's output keep `raw`, and intake gets about 12K tokens for 80 issues instead of about 180K. [inferred]
- **A route row plus a reference, not a skill.** A new prose skill costs many review rounds and adds surface. The stages already exist; the route only picks among them. [inferred]
- **The capture link fix is in this spec because intake's "new spec" action depends on it.** It is also a standalone bug fix. [inferred]

## Strategy Alignment

- Tracker determinism: what counts as "unlinked" becomes one flowctl answer instead of prose in two places. [strategy:Tracker determinism]

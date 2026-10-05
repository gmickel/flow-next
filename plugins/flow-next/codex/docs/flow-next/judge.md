# Optional Jev judgment

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


flow-next works the same with or without a TypeSafe API key. Every decision has
a working default path: code decides lifecycle facts, and the host decides the
rest from the route matrix and the repository. Routing and the QA gate never ask Jev. With a key, Jev (TypeSafe's
System One model) answers a few narrow questions in one HTTP request per
decision point, so the host reaches the same decision faster or cheaper. Jev
may change how long a decision takes and what it costs; it must not change
which decision is made. Existing review, QA, and merge gates run according to
their own contracts.

## Contents

- [Enable or disable](#enable-or-disable)
- [Where Jev decides and where it advises](#where-jev-decides-and-where-it-advises)
- [Runs without a key](#runs-without-a-key)
- [Presets and floors](#presets-and-floors)
- [Memory](#memory)
- [Exact question text](#exact-question-text)
- [Decision order](#decision-order)
- [Failure and transport contract](#failure-and-transport-contract)
- [Evaluation numbers of record](#evaluation-numbers-of-record)
- [TypeSafe API references](#typesafe-api-references)

## Enable or disable

Export `TYPESAFE_API_KEY` into the environment of the host that runs flow-next.
The command reads it only at call time; never put it in `.flow/config.json`,
a state file, a task receipt, or a prompt. There is no key-management ceremony
or SDK to install. Setup prints `Judge: off (TYPESAFE_API_KEY is not set).`
when the key is absent.

```bash
flowctl config get judge.enabled
flowctl config set judge.enabled false
flowctl config set judge.enabled true
flowctl judge --preset tier --task fn-1.1 --json
flowctl memory search "windows subprocess" --limit 15 --rerank --json
```

`judge.enabled` defaults to boolean `true`; a non-boolean value warns and behaves
as true. A missing key or `false` disables requests and leaves the default path.
The model is fixed to `jev-latest`; floors are preset constants.

## Where Jev decides and where it advises

| Decision | With a key | Host's part |
|---|---|---|
| Live spec lifecycle (PR tail, all done, recorded work route, direct or plan) | Code decides; Jev is not asked | None; the route is printed as `(code)` |
| Intake route kind, `tiny` included | Jev is not asked | The host decides from the route matrix, so a keyless run takes the same route |
| QA under `pipeline.qa=auto`: UI-observable criteria | Jev is not asked | The host decides from the acceptance and the repo |
| QA under `pipeline.qa=auto`: startable target | Code resolves a documented target; Jev is not asked | None; no target is invented |
| Research before work on a ready spec | Jev is not asked | Applies the route matrix's read-first rule |
| Fork: observable or preference | Optional hint on the host's own fork sentence | Decides; a hint never removes a fork the host found |
| Memory relevance | Reorders the top 15 BM25 hits; drops none | Picks the entries that apply from titles and snippets |
| Task tier | See the tier preset below | Unchanged by this contract |

Routing never asks Jev: `flowctl judge --preset route --spec <id>` returns the code lifecycle
decision and sends no request, key or no key, so a run with a key and one without take the same
route. The QA gate reads the startable target from the same route result
(`decision.startable_target_fact`) and decides the UI half itself, so its stage line never
carries a `jev` note.

## Runs without a key

`/flow-next:flow` checks once per run whether the judge can run: the key is
present (checked without printing it) and `judge.enabled` is not `false`. When
it cannot, flow prints `judge: off` once and makes no fork-gate call for
the rest of the run. The live-spec route call runs either way: its lifecycle
decision and PR observation come from code and return with
`available: false, reason: routing_is_code`. Memory search runs the same command either
way; without a key `--rerank` returns BM25 order and sends nothing.

The host prints `Route: <route> (host)` at intake and records QA stage lines,
key or no key. A judge that is on but fails keeps the same
default path and names the reason, `jev-unavailable(<reason>)`.

## Presets and floors

| Preset | Questions | Decision |
|---|---|---|
| `route` | None; code only, never sent | The live spec's lifecycle, decided in code (see [Decision order](#decision-order)). Intake routing is the host's. |
| `fork-gate` | Fork-kind Choice on the host's fork sentence | `observable` or `product_or_preference` at confidence >= 0.5 is a hint; otherwise `host`. Never `none`. |
| `memory-rerank` | One Score per BM25 hit, up to 15 | Reorder by score, descending; ties keep BM25 order; none dropped. |
| `tier` | Tier Choice and two Nouls | `mechanical` at confidence >= 0.8 selects the configured fast tier; `long_running` at >= 0.8 recommends a bridge. All other answers retain the current model. |

No preset predicts whether review, QA, or landing will pass, and none
decides whether QA runs.

## Memory

Plan, workers, and the memory scout use one shape:

```bash
flowctl memory search "<task sentence>" --limit 15 --rerank --json
```

The search returns up to 15 BM25 hits. With a key, one request scores them
and the command reorders them (`jev_score`, `jev_rank`) without dropping any;
`--limit` applies after the reorder. The judge receives each entry's id, title,
track, category, module, tags and snippet, never its path or BM25 score. The
host reads titles and snippets and keeps the entries that apply, on both paths.
Plan renders the result itself and does not spawn the memory scout to refine a
keyless result.

## Exact question text

Question IDs and instruction text below match the bundled preset registry.
`entry_N` substitutes the zero-based BM25 hit index, from 0 through 14.

### fork-gate

| ID | Type | Instruction text |
|---|---|---|
| `fork_kind` | choice | Assume an open design or behaviour fork exists. Classify what its answer depends on. |

Choice criteria:

- `observable`: Observable: behaviour, output, timing, layout, a failing case, a measurement
- `product_or_preference`: A product or preference call no experiment can settle: scope, priority, authority, taste, a business rule
- `none_of_the_above`: no criterion; fallback option

### memory-rerank

| ID | Type | Instruction text |
|---|---|---|
| `entry_0` | score | How does the memory entry `entries.0` bear on doing the task in `query`? |

Score levels, lowest first:

- It concerns a different module, tool, or failure mode; it would not come up while doing this task
- It shares this task's area or technology, but its lesson would not change how this task is done
- It applies to this task's files, tools, or failure mode; its lesson changes how this task is done

### tier

| ID | Type | Instruction text |
|---|---|---|
| `tier` | choice | Which is the minimum harness/model tier a senior engineer would assign this task to? Judge from the task text and the code facts beside it; pick the cheapest tier that would get it right first try. |
| `purely_mechanical_edit` | noul | Is this a purely mechanical edit (rename, config bump, mirror a doc, add a fixture, a one-place change with a known answer)? |
| `needs_long_uninterrupted_run` | noul | Would a competent implementer need a long uninterrupted run (multi-hour, many files, several subsystems) rather than one bounded turn? |

Choice criteria:

- `mechanical`: mechanical: a rename, a config bump, mirroring a doc, adding a test fixture, a one-place edit with a known answer; a fast, cheap model can do it and a wrong attempt is cheap to redo
- `moderate`: moderate: a bounded feature or fix in one module with its tests; the shape is known, the acceptance is concrete, no design judgment beyond the module
- `intelligent`: intelligent: design judgment, a cross-module change, ambiguous or negotiable acceptance, tradeoffs a senior engineer would want to weigh; the strongest available model in the session
- `long_running`: long_running: a multi-hour implementation spanning many files or subsystems that needs a long uninterrupted run in an isolated harness (a bridged external CLI on its own branch), not a turn in the session

Required standalone state fields: `text` for fork; `query` and `entries` for
memory. Tier fields are listed in the transport contract below.

## Decision order

For a live spec, code reads lifecycle facts in this order:

1. An observed PR routes to the existing PR tail. The live probe preserves open,
   merged, closed, and failed observations; a failed probe never means no PR.
2. Existing tasks all done routes to make-pr, after the applicable QA decision.
   Otherwise a `stale` plan review (the spec changed after its SHIP) routes to
   `plan_review`, whatever the task count.
3. An intentional plan with tasks, or one implicit owner under `no_plan: true`,
   continues work on the recorded route, preserving resume admission.
4. A ready spec with no tasks uses a recorded `no_plan: true` directly.
   Otherwise the positive plan signals (`asks_for_plan`, `separate_owners`,
   `staged_prs`) select plan; absent signals select direct work. False or missing
   `no_plan` is not a recorded plan choice. Whether to read before work is the
   host's, by the route matrix's read-first rule.
5. A spec that is not ready stays with the host for refinement, plan review,
   or proceeding.

Intake without a spec has no route call: the host picks the row from the
[route matrix](../../skills/flow-next-flow/references/route-matrix.md), and judges
whether a reported defect already carries a reproduction. `flow --explain`
prints its `Next:`, `Route:`, `Signal:`, `Skip/narrow:`, and `Why not the
alternatives:` lines from that row, without a judge call.

Tier selection happens before worker or scout dispatch. An explicit
`IMPLEMENTER:` override wins. A mechanical decision changes the spawn-model
parameter as well as the prompt's `IMPLEMENTER:` field; a missing fast-scout
model, or a host with neither model steering nor a suitable bridge, leaves the
model unchanged and says so. A long-running decision is a recommendation only.
Done summaries read the model that actually ran from the worker's return.

## Failure and transport contract

`flowctl judge` returns `available: false` and exit 0 for `no_key`, `disabled`,
`http_<status>`, `transport`, `timeout`, `bad_answer`, or `over_budget`. The caller
records the reason and takes its default host, static model, or BM25
path. A response missing a question or a sent option is `bad_answer`.
Unknown presets and invalid state files are command errors and exit nonzero.
See the [CLI contract](flowctl.md#judge) for the JSON envelope.

Requests use stdlib HTTP with a 10-second timeout per attempt. Only HTTP 429
and 529 retry, twice, after 1 and 2 seconds. State plus questions are estimated
at four characters per token against about 32k tokens; an oversized request
returns `over_budget` without sending. The judge itself writes neither state nor answers. Credentials never appear
in command output, receipts, stage lines, or logs.

A request sends its supplied artifact text to TypeSafe. Route state is never
sent. Tier state contains `task_title`, `task_body`,
`acceptance`, `touches_count`, `has_quick_commands`, and `repo`.

Callers expose which path they took:

```text
judge: off
Route: work_planned (code)
Route: build (host)
stage: qa - skipped(config: pipeline.qa=auto: no UI-observable criteria)
stage: qa - ran [target: <cmd>]
fork-gate: observable (host)
fork-gate: preference (host, jev hint product_or_preference 0.71)
memory: reranked (jev, 15 entries)
memory: bm25 (jev-unavailable(no_key))
Tier: mechanical (jev 0.88) -> <model>
Tier: long_running (jev 0.86) - bridge recommended
Tier: session (jev moderate 0.61)
```

## Evaluation numbers of record

The September 2026 evaluation measured a median 586 ms for the selected single
route request, with about 2,200 input tokens for an intent and 4,000-8,000 for a
spec body. At the evaluation's recorded rate of $46 per billion tokens, those
input volumes cost approximately $0.00010 and $0.00018-$0.00037 respectively,
before output tokens. These are historical evaluation measurements and cost
estimates, not a current price quote or a production latency guarantee. The
route preset no longer sends any request.

| Site | Evaluation result and bound |
|---|---|
| Clean review (retired preset; historical result) | 100/100 against the eyeball label; the regex recognized 5/12 in its comparison set. |
| Kind (retired; historical result) | 0.95 raw agreement on 196 stable samples; the 0.7 floor gave 85% held-out coverage at 95% agreement. Retired because keyed intake routes sent small features down heavier routes than keyless runs. |
| QA (retired; historical result) | 0.88 against a 0.71 baseline once code supplied the startable-target fact. Retired because keyless runs reached the same QA decision in the same step, so the call added 2-6 s and changed nothing. |
| Fork | 0.88 against 0.76 for the fork-present and kind pair on spec text; the hint on the host's own fork sentence has not been measured. |
| Memory | Precision@5 0.66 against BM25's 0.48, measured with the earlier score levels and floor; the reorder-only shape has not been measured. |
| Tier | 0.91 exact agreement and 121/121 within one tier; at 0.8, mechanical 20/20 and long-running 13/13 matched labels. |

These samples establish directional classification quality. They do not prove
that a cheaper worker will complete every task labeled mechanical or that
production runs achieve the same latency. The normal implementation review and
verification gates remain authoritative.

## TypeSafe API references

- [System One](https://docs.typesafe.ai/concepts/system-one.md) and [primitives](https://docs.typesafe.ai/primitives.md)
- [Choice](https://docs.typesafe.ai/primitives/choice.md), [Noul](https://docs.typesafe.ai/primitives/noul.md), and [Score](https://docs.typesafe.ai/primitives/score.md)
- [Confidence](https://docs.typesafe.ai/confidence.md) and [confidence routing](https://docs.typesafe.ai/patterns/confidence-routing.md)
- [Fan-out](https://docs.typesafe.ai/patterns/fan-out.md) and [building with System One](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md)
- [Structured instructions](https://docs.typesafe.ai/primitives/advanced.md), [HTTP API](https://docs.typesafe.ai/api.md), and [documentation index](https://docs.typesafe.ai/llms.txt)

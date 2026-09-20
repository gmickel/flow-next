# Optional Jev judgment

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


With a TypeSafe API key, flow-next answers narrow routing, task-tier, and memory
questions in one HTTP request per decision point. Code supplies the state and
applies fixed decision rules; the host handles uncertain answers. Existing
review, QA, and merge gates still run according to their own contracts.

## Contents

- [Enable or disable](#enable-or-disable)
- [Presets and floors](#presets-and-floors)
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
flowctl judge --preset qa-gate --spec fn-1 --json
flowctl memory search "windows subprocess" --rerank --json
```

`judge.enabled` defaults to boolean `true`; a non-boolean value warns and behaves
as true. A missing key or `false` disables requests and preserves the existing
fallback. The model is fixed to `jev-latest`; floors are preset constants.

## Presets and floors

| Preset | Questions | Decision |
|---|---|---|
| `route` | Kind Choice, 12 anchored Nouls, fork pair, QA Noul | Lifecycle first; intent/brief kind at confidence >= 0.7; otherwise host with top-three candidates. |
| `qa-gate` | UI-observable Noul | Run under `pipeline.qa=auto` only at >= 0.5 AND a startable target resolved by code. A skipped stage names the failing half. |
| `fork-gate` | Fork-present Noul and observable/preference Choice | Below 0.5 means no fork and no question; otherwise classify at confidence >= 0.5. `none_of_the_above` or low confidence returns to the host. |
| `memory-rerank` | One Score per BM25 hit, up to 15 | Levels `not relevant`, `tangential`, `directly relevant`; keep score >= 1.0, descending, capped at 10. Ties retain BM25 order. |
| `tier` | Tier Choice and two Nouls | `mechanical` at confidence >= 0.8 selects the configured fast tier; `long_running` at >= 0.8 recommends a bridge. All other answers retain the current model. |

The route request carries its fork and QA questions together. A routed skill
uses the standalone preset only when it does not already have that hop's
answers. QA configuration other than `auto` does not request a QA judgment.
`flowctl judge --preset qa-gate --spec <spec-id> --json` assembles the standalone
QA input and documented target in code. No preset predicts whether review, QA, or landing will pass.

## Exact question text

Question IDs and instruction text below match the bundled preset registry.
The route preset reuses the fork and QA questions shown under their standalone
presets. `entry_N` substitutes the zero-based BM25 hit index, from 0 through 14.

### route

| ID | Type | Instruction text |
|---|---|---|
| `kind` | choice | Which kind of work is this starting state? Route on content and context, never on input kind. The state carries `view` with its meaning. Pick none_of_the_above when no kind fits. |
| `reports_defect` | noul | Does the text report a defect: a bug report, console dump, crash, or failing behaviour, where the unknown is the cause and the risk is regression? |
| `defect_has_repro` | noul | If the text reports a defect, does it carry a concrete repro (steps, a failing command, a trace with a location, a case that shows it)? Answer no when there is no defect or no repro. |
| `structural_change_behaviour_kept` | noul | Is the text a structural change with behaviour meant to stay the same (rename, extract, inline, dedupe, move; callers to migrate or a shape to collapse) with no new behaviour named anywhere? |
| `names_metric_and_surface` | noul | Does the text name a measured slowness or a number the user wants moved once, with a metric and a surface the user can name (a trace or a repro)? |
| `repeated_metric_target` | noul | Does the text ask to improve one metric against a target number through repeated attempts on a harness that reruns cheaply? |
| `read_only_question` | noul | Is the text a read-only question (how does X work, why was Y built this way, are we sure about Z) whose deliverable is an answer rather than a change? |
| `theme_no_end_state` | noul | Is the text a theme or direction ("make X more Y") with no nameable end state, so no outcome and no scope boundary? |
| `no_written_direction` | noul | Does the text show that no written direction exists (target problem, users, or key metrics stated nowhere; repeated arguments about what matters)? |
| `large_idea_several_unknowns` | noul | Is the text one large singular idea with unclear boundaries and several consequential unknowns that block stating intent (too big for one capture)? |
| `names_unfamiliar_library_or_api` | noul | Does the text name a library, service, or API that the repository does not already use (an unfamiliar dependency that needs reading first)? |
| `tiny_one_context_change` | noul | Is the text a tiny, local, low-risk change that fits one implementation context (a one-context fix)? |
| `intent_and_boundaries_stateable` | noul | Can the intent and the boundaries of this effort be stated now (a clear meaningful idea), without further discovery? |

### qa-gate

| ID | Type | Instruction text |
|---|---|---|
| `ui_observable_criteria` | noul | Does the spec's acceptance describe UI behaviour a user could observe on a drivable surface (a screen, a page, a window, a rendered widget), as opposed to CLI output, file contents, or library behaviour? |

### fork-gate

| ID | Type | Instruction text |
|---|---|---|
| `fork_present` | noul | Does the text pose a design or behaviour fork (two named alternatives to choose between) that is still open? |
| `fork_kind` | choice | Assume an open design or behaviour fork exists. Classify what its answer depends on. |

Choice criteria:

- `observable`: Observable: behaviour, output, timing, layout, a failing case, a measurement
- `product_or_preference`: A product or preference call no experiment can settle: scope, priority, authority, taste, a business rule
- `none_of_the_above`: no criterion; fallback option

### memory-rerank

| ID | Type | Instruction text |
|---|---|---|
| `entry_0` | score | How relevant is `entries.0` to the task in `query`? |

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

Required standalone state fields: `acceptance` and
`startable_target_fact` for QA; `text` for fork; `query` and `entries` for
memory. Route and tier fields are listed in the transport contract below.

## Decision order

For a live spec, code reads lifecycle facts before classifying text:

1. An observed PR routes to the existing PR tail. The live probe preserves open,
   merged, closed, and failed observations; a failed probe never means no PR.
2. Existing tasks all done routes to make-pr, after the applicable QA decision.
3. An intentional plan with tasks, or one implicit owner under `no_plan: true`,
   continues work on the recorded route, preserving resume admission.
4. A ready spec with no tasks uses a recorded `no_plan: true` directly.
   Otherwise the positive plan signals (`asks_for_plan`, `separate_owners`,
   `staged_prs`) select plan; absent signals select direct work. False or missing
   `no_plan` is not a recorded plan choice. Research is recommended here when
   the unfamiliar-dependency Noul fires and no `## Resolved via Research` section exists.
5. A spec that is not ready stays with the host for refinement, plan review,
   or proceeding.

Live specs never ask the kind Choice. Intent and brief views ask the thirteen
content kinds plus `none_of_the_above`. Kind criteria copy the
[route matrix](../../skills/flow-next-flow/references/route-matrix.md)'s starting-state
and positive-signal cells verbatim, joined by a period. Lifecycle routes are
absent from those criteria. Below the kind floor, or on `none_of_the_above`,
the host receives only the top-three kinds and probabilities. Nouls feed code
and the `Signal:` line, never facts for the host to reconsider.

`flow --explain` uses that same request for `Next:`, `Route:`, `Signal:`,
`Skip/narrow:`, and `Why not the alternatives:`. The last line names the next
two candidates; a below-floor recommendation names all three and says the host
decides. The two judgment hints `tiny_one_context_change` and
`intent_and_boundaries_stateable` never determine the route.

Tier selection happens before worker or scout dispatch. An explicit
`IMPLEMENTER:` override wins. A mechanical decision changes the spawn-model
parameter as well as the prompt's `IMPLEMENTER:` field; a missing fast-scout
model, or a host with neither model steering nor a suitable bridge, leaves the
model unchanged and says so. A long-running decision is a recommendation only.
Done summaries read the model that actually ran from the worker's return.

## Failure and transport contract

`flowctl judge` returns `available: false` and exit 0 for `no_key`, `disabled`,
`http_<status>`, `transport`, `timeout`, `bad_answer`, or `over_budget`. The caller
records the reason and takes its previous host, static model, or BM25
path. A response missing a question or a sent option is `bad_answer`.
Unknown presets and invalid state files are command errors and exit nonzero.
See the [CLI contract](flowctl.md#judge) for the JSON envelope.

Requests use stdlib HTTP with a 10-second timeout per attempt. Only HTTP 429
and 529 retry, twice, after 1 and 2 seconds. State plus questions are estimated
at four characters per token against about 32k tokens; an oversized request
returns `over_budget` without sending. Route assembly takes only the first
100,000 characters of a long spec body and records `spec_body_truncated: true`.
The judge itself writes neither state nor answers. Credentials never appear
in command output, receipts, stage lines, or logs.

A request sends its supplied artifact text to TypeSafe. Route state includes
only `view`, `view_meaning`, `repo`, `intent` or `spec_title` plus `spec_body`,
`status`, `ready`, `no_plan`, task counts, PR observations, and
`startable_target_fact` (plus the truncation marker when needed). Tier state
contains `task_title`, `task_body`, `acceptance`, `touches_count`,
`has_quick_commands`, and `repo`.

Callers expose which path they took:

```text
Route: defect (jev 0.91)
Route: host (jev below floor: build 0.52, tiny 0.31, defect 0.10)
Route: host (jev-unavailable(timeout))
stage: qa - skipped(config: pipeline.qa=auto: no UI-observable criteria (jev 0.12))
stage: qa - ran (jev ui 0.84, target: <cmd>)
fork-gate: none (jev 0.08)
fork-gate: observable (jev 0.77)
fork-gate: preference (jev 0.71)
fork-gate: host (jev below floor)
memory: reranked (jev, 15 -> 6)
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
estimates, not a current price quote or a production latency guarantee.

| Site | Evaluation result and bound |
|---|---|
| Clean review (retired preset; historical result) | 100/100 against the eyeball label; the regex recognized 5/12 in its comparison set. |
| Kind | 0.95 raw agreement on 196 stable samples; the 0.7 floor gave 85% held-out coverage at 95% agreement. |
| QA | 0.88 against a 0.71 baseline once code supplied the startable-target fact. |
| Fork | 0.88 against 0.76; invented forks fell from 12 to 1. |
| Memory | Precision@5 0.66 against BM25's 0.48. |
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

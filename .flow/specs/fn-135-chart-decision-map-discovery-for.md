# fn-135 chart: decision-map discovery for oversized ideas (pre-capture)

## Goal & Context
<!-- scope: business -->

Everything from `capture` onwards is heavily exercised and deliberately opinionated. The stage *before* capture is not. Field coaching keeps surfacing the same two-sided gap:

- `/flow-next:prospect` gives you a **ranked idea**. `/flow-next:capture` wants **intent it can write down**. Between them, for an effort that is genuinely large and genuinely foggy, there is nothing. Teams either capture too early (a spec full of `[inferred]` criteria that the interview then has to demolish) or hold a series of unstructured meetings whose output evaporates.
- The ideation edge is the most company-specific part of any delivery process, so the answer is not to bolt a fixed discovery ceremony onto the front. It is to ship a **composable** discovery primitive that produces a briefing artefact, which is exactly what the shipped [prototype-driven-specs](https://flow-next.dev/strategy/prototype-driven-specs/) doctrine tells people to bring their own front door for.

`/flow-next:chart` fills that gap. It takes **one loose idea that is too big for a single capture session and wrapped in unknowns**, and finds the route to it by resolving one decision at a time until the effort can be captured as one or more specs.

The unit of a chart is a **question whose resolution is a decision**, not a slice of a build. This is what separates chart from `plan`: plan decomposes work that is already understood; chart makes an effort understandable enough to be worth planning.

Chart is also where the evidence-first route family stops being prose and becomes executable. The doctrine says "let something real answer the question, then capture the answer", and names the routes: prototype, probe, reproduce, eval, bake-off, research, spike. Chart's question types **are** those routes, so the doctrine page and the skill teach the same thing.

### Why this is not `plan` with different words

| | `chart` | `plan` |
|---|---|---|
| Input | A loose idea; the route is not visible | A spec that is ready |
| Unit | A question resolving to a decision | A task resolving to a diff |
| Done when | Nothing is left to decide before someone builds | Every task is executed and evidenced |
| Output | A briefing artefact, handed to `capture` | Tasks with dependencies and waves |
| Fails by | Charting fog it cannot yet see | Sizing tasks past one worker context |

### Why this is not `prospect`

`prospect` answers *"what should we do?"* across a focus area and returns ranked candidates. `chart` answers *"how do we get from this one idea to something specifiable?"*. Prospect is upstream and plural; chart is downstream and singular. A chart may legitimately begin at a prospect candidate.

## Architecture & Data Models
<!-- scope: technical -->

### The chart object

A chart is git-native like a spec, and lives beside them:

- `.flow/charts/<chart-id>.md` -- the map body (below).
- `.flow/charts/<chart-id>.json` -- metadata sidecar: `id`, `title`, `destination`, `status` (`open|done|abandoned`), `created`, `questions[]`, `tracker` projection keys, `produced_specs[]`.

Chart ids share the repo prefix and allocator with specs (`<prefix>-<n>`) but carry a distinct kind so `flowctl list` can render them separately and spec-id collision logic (fn-134) applies unchanged.

The map body is an **index, not a store**. A decision lives in exactly one place -- its question record -- so the map gists and links, never restates:

```markdown
# <chart-id> <Title>

## Destination
<What reaching the end of this chart looks like: the spec(s), the decision, or the
change this effort is finding its way to. One or two lines. Every session orients
to it before choosing a question.>

## Notes
<Domain. Skills every session should consult. Standing preferences for this effort.>

## Decisions so far
- [<resolved question title>](<link>) -- <one-line gist of the answer>

## Not yet specified
<Fog: in-scope unknowns you can tell are coming but cannot yet phrase sharply.>

## Out of scope
<Ruled beyond the destination. Closed; never graduates.>
```

### The question object

Each question is a child record of the chart, one per file under `.flow/charts/<chart-id>/<n>.md` with a JSON sidecar, mirroring the spec/task split so existing readers, the tracker projector, and `flowctl anchor` need no new transport.

Body is deliberately minimal -- the question, nothing else:

```markdown
## Question
<the decision or investigation this resolves>
```

Sidecar fields: `id`, `chart`, `type`, `status` (`open|resolved|out-of-scope`), `blocked_by[]`, `claimed_by`, `assets[]` (branch refs, evidence paths, tracker URLs), `answer` (written on resolution).

Sized to one worker context (~100k tokens), same budget as a task.

### Question types = the evidence-first routes

Each question carries exactly one type. The type decides who resolves it and how.

| Type | Attended? | Resolves by |
|---|---|---|
| `research` | unattended | A scout subagent reads docs, upstream sources, or knowledge bases and returns a fact the decision waits on |
| `probe` | unattended | Measure or reproduce against the real system: load test, profiling run, a failing test that reproduces a reported defect |
| `eval` | unattended | Bake-off or benchmark across candidates on real fixtures; returns a winner and why |
| `prototype` | **attended** | Throwaway code that answers a fidelity question. Reacting to the artefact *is* the work, so this type never self-resolves |
| `interview` | **attended** | Conversation, one question at a time, via `/flow-next:interview` machinery on the chart rather than a spec. The default type |
| `task` | either | Manual work that unblocks a *decision* (provision access, obtain credentials, move data so its shape can be seen). The one type that does rather than decides; earns its place by unblocking |

Attended types never resolve without the human's side of the exchange. An agent that answers its own `prototype` or `interview` question has broken the contract, and this is an explicit gate, not a convention.

### Frontier, fog, and scope

- **Blocking** uses `blocked_by[]`, reusing the task dependency resolver unchanged. When a chart is projected to a tracker, blocking projects onto the tracker's native dependency relation so the frontier renders in the tracker UI without opening the chart.
- **Frontier** = open, unblocked, unclaimed questions. `flowctl chart frontier <chart-id>` returns it.
- **Fog** (`## Not yet specified`) is deliberate incompleteness. The test for fog-vs-question is whether the question can be **stated** precisely now, not whether it can be **answered** now. A sharp but blocked question is a question. A vague one is fog. Resolving a question graduates whatever fog it made specifiable into fresh questions, and clears that patch from the section so it lives in exactly one place.
- **Out of scope** is a scoping act, not a route step. A question exposed as sitting past the destination is closed with a one-line reason under `## Out of scope`, and stays out of `## Decisions so far`, which records the route actually walked.

### Tracker projection

Charts reuse the existing tracker projection layer (projection, not coordination). When `tracker.charts` is on, the chart projects as a parent issue and its questions as children, with native blocking edges. This is the direct answer to the field ask for a control plane for POs, PMs, BAs, and QE who should not need a repo checkout or a branch to participate in discovery. The chart files stay the source of truth; the tracker never drives chart state.

### Exit: the briefing artefact

A chart is done when the frontier is empty and the fog is empty. On close, chart writes `.flow/charts/<chart-id>-briefing.md`: the destination, every decision with its gist and link, the assets (prototype branches, evidence paths, probe results), and the explicit out-of-scope list.

That briefing is a first-class `capture` input, which closes the loop with the shipped doctrine: discovery produced evidence, and the spec records what the evidence proved.

## API Contracts
<!-- scope: technical -->

### Skill

`/flow-next:chart` in two modes, disambiguated by argument.

```
/flow-next:chart "<loose idea>"              # chart mode: name the destination, sketch the map
/flow-next:chart <chart-id>                  # work mode: resolve the next frontier question
/flow-next:chart <chart-id> --question <n>   # work mode, human picks the question
/flow-next:chart <chart-id> --status         # render map + frontier, resolve nothing
```

Plain-language equivalents are required, per the no-syntax-to-memorize contract: "chart out the multi-tenant migration", "work the next question on the billing chart", "what's left to decide on fn-140".

### flowctl

| Command | Contract |
|---|---|
| `flowctl chart create --title <t> --destination <d>` | Allocates a chart id, writes body + sidecar |
| `flowctl chart show <id>` | Map body + counts (resolved / open / blocked / fog) |
| `flowctl chart frontier <id>` | Open, unblocked, unclaimed questions, dependency-ordered |
| `flowctl chart add-question <id> --type <t> --body-file <f> [--blocked-by <n,...>]` | Creates a question; two-pass wiring supported (create, then wire) |
| `flowctl chart claim <id>.<n>` | Atomic claim; refuses an already-claimed question |
| `flowctl chart resolve <id>.<n> --answer-file <f> [--assets <json>]` | Records the answer, closes the question, appends to `## Decisions so far` |
| `flowctl chart out-of-scope <id>.<n> --reason <r>` | Closes without a decision; writes the `## Out of scope` line |
| `flowctl chart briefing <id>` | Emits the briefing artefact; refuses while the frontier or fog is non-empty unless `--force` |
| `flowctl chart list` | Open charts with progress |

All commands take `--json`. Machine-readable output is the contract for autonomous drivers.

### Verdict grammar

Work mode terminates with one greppable line, matching the pilot convention so host `/loop` and `/goal` drivers can drive discovery the same way they drive the build loop:

```
CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> question=<n> reason="<one line>"
```

`NEEDS_HUMAN` is the terminal verdict for an attended question reached by an unattended driver -- the loop parks it rather than self-answering.

## Edge Cases & Constraints
<!-- scope: technical -->

- **One question per session, with one exception.** Resolving more than one attended question per session reintroduces the context collapse the chart exists to prevent. Unattended types (`research`, `probe`, `eval`) may fan out in parallel, since each returns a fact rather than consuming judgment.
- **Charting resolves nothing.** Chart mode ends after the map and the first questions exist. A charting session that starts answering its own questions has skipped the human's scoping act.
- **The agent never answers an attended question.** Hard gate, not guidance. A `prototype` or `interview` question resolved inside an unattended run is a contract violation and must terminate `NEEDS_HUMAN`.
- **Chart never writes a spec.** It hands a briefing to `capture`. Letting chart author specs directly would let inferred discovery content bypass capture's source-tagging and read-back, which is exactly the guarantee the ratchet depends on.
- **Chart never sets `ready`.** Promotion stays a human act, unchanged.
- **Charts are not required.** A small, well-understood effort goes straight to `capture`. Reaching for a chart on a two-day feature is the same error as running a full interview on a one-line fix. `/flow-next:chart` on an idea with no fog must say so and stop rather than manufacture questions.
- **Abandoned charts.** An effort killed mid-discovery closes `abandoned` with its decisions intact. The decisions were paid for and stay searchable; a future chart may cite them.
- **Concurrency.** Multiple sessions may work one chart. Claims are atomic and checked before any work; a stale claim (configurable age) can be broken with a recorded note.
- **Fog is not a backlog.** `## Not yet specified` must not be pre-sliced into question-shaped pieces. One fog patch may graduate into several questions, or none.
- **No new tracker adapters.** Chart projection rides the existing four (Linear, GitHub, GitLab, Jira) or degrades to local-only.
- **Spec prose must not trip destructive-command guards.** Chart bodies, question bodies, and briefings are frequently piped through shells by drivers and skills. Documentation examples inside these artefacts must avoid literal destructive command strings, which guard packs match on sight regardless of context. This spec is itself a worked example: an earlier draft was blocked by dcg for quoting an uninstall command in prose.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `/flow-next:chart "<idea>"` produces a chart with a named destination, an empty decisions ledger, at least one question, and fog recorded under `## Not yet specified`; it resolves no questions in that session.
- **R2:** Charting an idea that surfaces no fog terminates without creating a chart, and states that the effort is small enough to capture directly.
- **R3:** Every question carries exactly one type from `research | probe | eval | prototype | interview | task`, and the type is required at creation.
- **R4:** `flowctl chart frontier <id>` returns only open, unblocked, unclaimed questions, dependency-ordered, and is the sole selection input for work mode.
- **R5:** Work mode claims a question atomically before any work; a second session claiming the same question fails with a non-zero exit and a distinguishable error.
- **R6:** Resolving a question writes the answer to its record, closes it, and appends exactly one gist line with a link to `## Decisions so far`. The map body never restates the answer.
- **R7:** Resolving a question graduates any newly-specifiable fog into questions and removes that patch from `## Not yet specified`, so no content exists in both places.
- **R8:** An attended question (`prototype`, `interview`) reached in an unattended run terminates `CHART_VERDICT=NEEDS_HUMAN` without writing an answer.
- **R9:** Unattended questions (`research`, `probe`, `eval`) may be dispatched in parallel within one session; attended questions are limited to one per session.
- **R10:** `flowctl chart out-of-scope` closes a question, writes a one-line reason under `## Out of scope`, and produces no entry under `## Decisions so far`.
- **R11:** `flowctl chart briefing <id>` refuses with a non-zero exit while the frontier or fog is non-empty, unless `--force` is passed.
- **R12:** The emitted briefing contains the destination, every decision with gist and link, all recorded assets, and the out-of-scope list; `/flow-next:capture` accepts it as an input without transformation.
- **R13:** Chart writes no file under `.flow/specs/` and never mutates a spec's `ready` flag.
- **R14:** Every `flowctl chart` subcommand supports `--json` and emits schema-valid output.
- **R15:** Work mode terminates with exactly one `CHART_VERDICT=` line matching the documented grammar.
- **R16:** With `tracker.charts` enabled, a chart projects as a parent issue with questions as children and native blocking edges; with it disabled or no tracker configured, all chart operations succeed local-only.
- **R17:** Every documented flag has a plain-language equivalent that reaches the same behavior.
- **R18:** Chart ids allocate through the same allocator as specs, and a chart and spec never share an id.
- **R19:** Docs ship with the skill: a `skills/chart.mdx` page on flow-next.dev, entries in **both** nav sources, a changelog entry, GLOSSARY terms (chart, question, frontier, fog, destination, briefing artefact), and a cross-link from the prototype-driven-specs page.
- **R20:** No chart-authored artefact (chart body, question body, briefing) emitted by the skill contains a literal destructive shell command string; the skill's own documentation examples use prose descriptions instead.

## Boundaries
<!-- scope: business -->

- **Not a project-management tool.** Chart tracks decisions in flight for one effort, then closes. It is not a roadmap, a portfolio view, or a backlog.
- **Not a replacement for `prospect` or `strategy`.** Chart starts from one idea that already exists.
- **Not a builder.** Only `task` questions do anything, and only to unblock a decision. Charting an effort must not become a way to smuggle implementation past plan and review.
- **Not a spec author.** Output is a briefing; `capture` remains the only path into `.flow/specs/`.
- **No new review backends, trackers, or hosts.** Chart composes with what exists.
- **Autonomous end-to-end discovery is out of scope for v1.** Unattended question types may be driven by a loop, but a chart that reaches only attended questions parks. Fully autonomous discovery would require an agent to stand in for product judgment, which is the one thing the doctrine says it must not do.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Two independent pressures land on the same missing primitive.

**Field pressure.** In rollout conversations the pre-capture stage is where teams stall. The observed failure is not that people dislike specs; it is that they are asked to write one before the effort is knowable, produce a spec full of guesses, and then conclude that spec-first does not work. Meanwhile the discovery that *would* have made the spec good happens in meetings and evaporates. The same conversations produce the recurring ask for a surface where product, BA, and quality can participate without a repo checkout.

**Doctrine pressure.** flow-next now ships an explicit position: the spec is a ratchet not a gate, the spec is an output of discovery, and the way to get a good one is to let something real answer the question first. That doctrine currently has cookbook recipes and a strategy page, but no primitive that *structures* a discovery effort too large to hold in one session. Chart is the doctrine made executable, which is why its question types are the route family verbatim rather than a fresh taxonomy.

The timing argument: the ideation edge was left deliberately open, and that was correct. Chart does not close it. It adds one composable primitive inside the open edge, whose output is a briefing artefact -- the same artefact a company-specific front door would emit. Teams that already have their own discovery process keep it and ignore chart.

### Implementation Tradeoffs
<!-- scope: technical -->

**Files-first, tracker-optional.** Charts live in `.flow/` for the same reasons specs do: portable, greppable, diffable, no hosted dependency, and deleting the `.flow/` directory still uninstalls cleanly. Tracker projection is additive. The alternative (tracker as the store) was rejected: it would make discovery unavailable offline, tie the primitive to four vendor APIs, and invert projection-not-coordination.

**Question types mirror the doctrine rather than inventing a taxonomy.** Rejected a generic `question` type with free-form resolution. Typing the question is what makes the route selectable and the attended/unattended boundary mechanical, and reusing the published route family means one concept is taught in one vocabulary across the strategy page, the cookbook, and the skill.

**One attended question per session.** Rejected batching. The context-collapse failure mode is well-evidenced across the orchestration work, and a decision made at the tail of a long session is measurably worse than one made fresh. Unattended types are exempted because they return facts rather than consume judgment.

**Fog as a first-class section rather than pre-created placeholder questions.** Rejected auto-slicing fog into stub questions: a fog patch may graduate into several questions or none, and stub questions pollute the frontier with items nobody can act on. The state-it-vs-answer-it test is the cheapest reliable discriminator.

**Chart hands off to `capture` rather than writing specs.** The tempting shortcut is to have a completed chart emit specs directly. Rejected: capture owns source-tagging and the read-back consent loop, and letting discovery content bypass them would put `[inferred]` material into specs unlabelled -- attacking the exact guarantee the ratchet provides.

**Named `chart`, not `map`.** `/flow-next:map` is already the clawpatch feature-map wrapper. `chart` reads as both noun and verb, matches the destination/frontier/fog vocabulary, and does not collide.

**Deferred to a follow-up:** cross-chart decision reuse (citing a prior chart's decision as an answer), chart templates for recurring discovery shapes, and a visual frontier renderer via the render-lens layer. All are additive and none block v1.

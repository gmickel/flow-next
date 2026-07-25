# fn-135 chart: decision-map discovery for oversized ideas (pre-capture)

## Goal & Context
<!-- scope: business -->

Everything from `capture` onwards is heavily exercised and deliberately opinionated. The stage *before* capture is not. Field coaching keeps surfacing the same two-sided gap:

- `/flow-next:prospect` gives you a **ranked idea**. `/flow-next:capture` wants **intent it can write down**. Between them, for an effort that is genuinely large and genuinely foggy, there is nothing. Teams either capture too early (a spec full of `[inferred]` criteria that the interview then has to demolish) or hold a series of unstructured meetings whose output evaporates.
- The ideation edge is the most company-specific part of any delivery process, so the answer is not to bolt a fixed discovery ceremony onto the front. It is to ship a **composable** discovery primitive that produces a briefing package, which is exactly what the shipped [prototype-driven-specs](https://flow-next.dev/strategy/prototype-driven-specs/) doctrine tells people to bring their own front door for.

`/flow-next:chart` fills that gap. It takes **one loose idea that is too big for a single capture session and wrapped in unknowns**, and finds the route to it by resolving one decision at a time until the effort can be captured as one or more specs.

The unit of a chart is a **decision** -- a question whose resolution settles something, not a slice of a build. This is what separates chart from `plan`: plan decomposes work that is already understood; chart makes an effort understandable enough to be worth planning.

Chart is also where the evidence-first route family stops being prose and becomes executable. The doctrine says "let something real answer the question, then capture the answer", and names the routes: prototype, probe, reproduce, eval, bake-off, research, spike. A chart's decision types **are** those routes, so the doctrine page and the skill teach the same thing.

### Why this is not `plan` with different words

| | `chart` | `plan` |
|---|---|---|
| Input | A loose idea; the route is not visible | A spec that is ready |
| Unit | A decision (D-ID) | A task resolving to a diff |
| Done when | Nothing is left to decide before someone builds | Every task is executed and evidenced |
| Output | A briefing package, handed to `capture` | Tasks with dependencies and waves |
| Fails by | Charting what it cannot yet see | Sizing tasks past one worker context |

### Why this is not `prospect`

`prospect` answers *"what should we do?"* across a focus area and returns ranked candidates. `chart` answers *"how do we get from this one idea to something specifiable?"*. Prospect is upstream and plural; chart is downstream and singular. A chart may legitimately begin at a prospect candidate.

## Architecture & Data Models
<!-- scope: technical -->

### The chart object

A chart is git-native like a spec, and lives beside them:

- `.flow/charts/<chart-id>.md` -- the map body (below).
- `.flow/charts/<chart-id>.json` -- metadata sidecar: `id`, `title`, `outcome`, `status` (`open|done|abandoned`), `created`, `decisions[]`, `tracker` projection keys, `produced_specs[]`.

Chart ids share the repo prefix and allocator with specs (`<prefix>-<n>`) but carry a distinct kind so `flowctl list` can render them separately and spec-id collision logic (fn-134) applies unchanged.

The map body reuses spec section names wherever the meaning matches, so a reader who knows a spec can read a chart cold. It is an **index, not a store** -- a decision's detail lives in exactly one place, its own record, so the map gists and links but never restates:

```markdown
# <chart-id> <Title>

## Outcome
<What reaching the end of this chart looks like: the spec(s), the decision, or the
change this effort is finding its way to. One or two lines. Every session re-anchors
on it before choosing a decision.>

## Notes
<Domain. Skills every session should consult. Standing preferences for this effort.>

## Decisions
<!-- the ledger: one line per resolved decision, append-only, D-IDs never reused -->
- **D1:** <one-line gist of the answer> -- [<record>](<link>)
- ~~**D3:**~~ <gist> -- superseded by **D9** -- [<record>](<link>)

## Open Questions
<!-- in-scope unknowns not yet sharp enough to be a decision record -->

## Boundaries
<!-- ruled beyond the Outcome; closed, never graduates -->
```

`## Open Questions` and `## Boundaries` carry the same meaning here as in a spec: parked unknowns, and what is deliberately not being done. `## Outcome` is the chart's `Goal & Context`.

### The decision record

Each decision is a child record of the chart, one per file under `.flow/charts/<chart-id>/<n>.md` with a JSON sidecar, mirroring the spec/task split so existing readers, the tracker projector, and `flowctl anchor` need no new transport.

Body is deliberately minimal -- the question, nothing else:

```markdown
## Question
<what this decision settles>
```

Sidecar fields: `id` (D-ID), `chart`, `type`, `status` (`open|resolved|superseded|out-of-scope`), `blocked_by[]`, `depends_on[]`, `supersedes[]`, `superseded_by`, `claimed_by`, `assets[]` (branch refs, evidence paths, tracker URLs), `answer` (written on resolution).

Sized to one worker context (~100k tokens), same budget as a task.

**D-IDs follow the R-ID discipline exactly**: allocated sequentially from D1, append-only, never renumbered and never reused. A removed or superseded decision leaves a gap. D-IDs are the load-bearing identity of a decision across the ledger, the records that depend on it, the briefing, and the spec that eventually cites it.

### Decision types = the evidence-first routes

Each decision carries exactly one type. The type decides who resolves it and how.

| Type | Attended? | Resolves by |
|---|---|---|
| `research` | unattended | A scout subagent reads docs, upstream sources, or knowledge bases and returns a fact the decision waits on |
| `probe` | unattended | Measure or reproduce against the real system: load test, profiling run, a failing test that reproduces a reported defect |
| `eval` | unattended | Bake-off or benchmark across candidates on real fixtures; returns a winner and why |
| `prototype` | **attended** | Throwaway code that answers a fidelity question. Reacting to the artefact *is* the work, so this type never self-resolves |
| `interview` | **attended** | Conversation, one question at a time, via `/flow-next:interview` machinery on the chart rather than a spec. The default type |
| `task` | either | Manual work that unblocks a *decision* (provision access, obtain credentials, move data so its shape can be seen). The one type that does rather than decides; earns its place by unblocking |

Attended types never resolve without the human's side of the exchange. An agent that answers its own `prototype` or `interview` decision has broken the contract, and this is an explicit gate, not a convention. This is the same consent boundary the autonomy loops hold, expressed one stage earlier.

### Frontier, parked questions, and scope

- **Blocking** uses `blocked_by[]`, reusing the task dependency resolver unchanged. When a chart is projected to a tracker, blocking projects onto the tracker's native dependency relation so the frontier renders in the tracker UI without opening the chart.
- **Frontier** = open, unblocked, unclaimed decisions -- the same word and the same shape `/flow-next:work` already uses for the ready task frontier. `flowctl chart frontier <chart-id>` returns it.
- **`## Open Questions`** holds deliberate incompleteness: in-scope unknowns you can tell are coming but cannot yet phrase sharply. The test for parked-vs-decision is whether the question can be **stated** precisely now, not whether it can be **answered** now. A sharp but blocked question is a decision record. A vague one parks. Resolving a decision graduates whatever it made specifiable into fresh decision records, and clears that entry from `## Open Questions` so it lives in exactly one place.
- **`## Boundaries`** is a scoping act, not a route step. A decision exposed as sitting past the Outcome is closed with a one-line reason under `## Boundaries`, and stays out of `## Decisions`, which records the route actually walked.

### Supersession: when a later decision invalidates an earlier one

Resolved decisions are **immutable**, on the same principle as a completed spec: they are change history, not a wiki. A later finding never edits or deletes an earlier answer. It supersedes it.

`flowctl chart resolve <id>.<n> --supersedes D3` does four things atomically:

1. Writes the new answer and closes the new decision normally.
2. Flips `D3.status` to `superseded` and sets `D3.superseded_by`.
3. Rewrites D3's ledger line as struck-through with a pointer to the superseding D-ID. The line is **never removed** -- the route actually walked includes its wrong turns, and deleting them invites the same wrong turn twice.
4. Reports every open decision declaring `depends_on: D3` and **re-opens** them (status back to `open`, claim cleared), because a decision made on a now-false premise is not safe to keep. `--keep-dependents` suppresses the re-open when the dependency was incidental, and records that judgment on the record.

The briefing carries superseded decisions in their own section. They are evidence: they tell whoever reads the spec later which alternatives were tried and abandoned during discovery, which is exactly the material `## Decision Context` wants.

### Exit: the briefing package, and the spec split

A chart is done when the frontier is empty and `## Open Questions` is empty.

**A chart may produce more than one spec.** A large effort routinely splits along boundaries only discovered *during* discovery, so the split is decided at briefing time rather than guessed at charting time. `flowctl chart briefing <id>`:

1. Clusters the resolved decisions and **proposes** N spec boundaries with a one-line rationale for each, and names any decision that lands in more than one cluster as **shared context** rather than a duplicated requirement.
2. Presents the proposal for confirmation before writing anything, matching capture's read-back consent pattern. The human may merge, split further, or override.
3. Emits `.flow/charts/<id>-briefing.md` as the index (Outcome, the full ledger, superseded decisions, boundaries) plus `.flow/charts/<id>-briefing-<k>.md` per proposed spec, each carrying the shared Outcome, the decisions in its cluster, and their assets.

Default is **N=1**; a split is only proposed when the decision clusters are genuinely disjoint. Once `capture` runs, `produced_specs[]` records the D-ID-to-spec mapping, so a spec traces back to the decisions that produced it and a superseded decision can be audited against anything that cited it.

### Cost is reported before it is spent

Discovery cost is dominated by **attended** decisions, because each one is a session with a human in it. Chart mode therefore ends with an estimate before it persists anything:

```
9 decisions: 5 unattended (parallel, ~1 session), 4 attended (~4 sessions).
Estimated 4-5 working sessions with you.
```

`flowctl chart show` carries the same line for the remaining frontier, so the outstanding human cost is visible at a glance rather than discovered three weeks in.

## API Contracts
<!-- scope: technical -->

### Skill

`/flow-next:chart` in two modes, disambiguated by argument.

```
/flow-next:chart "<loose idea>"              # chart mode: name the Outcome, sketch the map
/flow-next:chart <chart-id>                  # work mode: resolve the next frontier decision
/flow-next:chart <chart-id> --decision <n>   # work mode, human picks the decision
/flow-next:chart <chart-id> --status         # render map + frontier + remaining cost, resolve nothing
```

Plain-language equivalents are required, per the no-syntax-to-memorize contract: "chart out the multi-tenant migration", "work the next decision on the billing chart", "what's left to decide on fn-140".

### flowctl

| Command | Contract |
|---|---|
| `flowctl chart create --title <t> --outcome <o>` | Allocates a chart id, writes body + sidecar |
| `flowctl chart show <id>` | Map body + counts (resolved / open / blocked / parked) + remaining attended-session estimate |
| `flowctl chart frontier <id>` | Open, unblocked, unclaimed decisions, dependency-ordered |
| `flowctl chart add-decision <id> --type <t> --body-file <f> [--blocked-by <D,...>] [--depends-on <D,...>]` | Allocates the next D-ID; two-pass wiring supported (create, then wire) |
| `flowctl chart claim <id>.<D>` | Atomic claim; refuses an already-claimed decision |
| `flowctl chart resolve <id>.<D> --answer-file <f> [--assets <json>] [--supersedes <D,...>] [--keep-dependents]` | Records the answer, closes it, appends the ledger line, applies supersession |
| `flowctl chart out-of-scope <id>.<D> --reason <r>` | Closes without a decision; writes the `## Boundaries` line |
| `flowctl chart briefing <id> [--split <k>] [--force]` | Proposes the spec split, then emits the index plus one briefing per spec |
| `flowctl chart list` | Open charts with progress and remaining attended cost |

All commands take `--json`. Machine-readable output is the contract for autonomous drivers.

### Verdict grammar

Work mode terminates with one greppable line, matching the pilot convention so host `/loop` and `/goal` drivers can drive discovery the same way they drive the build loop:

```
CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="<one line>"
```

`NEEDS_HUMAN` is the terminal verdict for an attended decision reached by an unattended driver -- the loop parks it rather than self-answering.

## Edge Cases & Constraints
<!-- scope: technical -->

- **One decision per session, with one exception.** Resolving more than one attended decision per session reintroduces the context collapse the chart exists to prevent. Unattended types (`research`, `probe`, `eval`) may fan out in parallel, since each returns a fact rather than consuming judgment.
- **Charting resolves nothing.** Chart mode ends after the map, the first decision records, and the cost estimate exist. A charting session that starts answering its own decisions has skipped the human's scoping act.
- **The agent never answers an attended decision.** Hard gate, not guidance. A `prototype` or `interview` decision resolved inside an unattended run is a contract violation and must terminate `NEEDS_HUMAN`.
- **Chart never writes a spec.** It hands a briefing to `capture`. Letting chart author specs directly would let inferred discovery content bypass capture's source-tagging and read-back, which is exactly the guarantee the ratchet depends on.
- **Chart never sets `ready`.** Promotion stays a human act, unchanged.
- **Charts are not required.** A small, well-understood effort goes straight to `capture`. Reaching for a chart on a two-day feature is the same error as running a full interview on a one-line fix. `/flow-next:chart` on an idea with nothing parked must say so and stop rather than manufacture decisions.
- **Charts have a size ceiling.** Past `chart.maxDecisions` (default 12) at charting time, chart refuses to persist and proposes either narrowing the Outcome or splitting into two charts, because a 20-decision chart is a quarter of discovery masquerading as one effort. `--force` overrides and records that it was forced. The ceiling is a charting-time guard only; decisions graduated later from `## Open Questions` may legitimately carry a chart past it.
- **A superseded decision is never deleted.** Its ledger line is struck through, its record stays readable, and it appears in the briefing under its own heading. Reversals are the most valuable thing a chart learns.
- **Supersession cascades are reported, never silent.** Re-opening dependents clears their claims, so a session holding one must re-claim; the re-open reason names the superseding D-ID.
- **Abandoned charts.** An effort killed mid-discovery closes `abandoned` with its decisions intact. The decisions were paid for and stay searchable; a future chart may cite them.
- **Concurrency.** Multiple sessions may work one chart. Claims are atomic and checked before any work; a stale claim (configurable age) can be broken with a recorded note.
- **`## Open Questions` is not a backlog.** It must not be pre-sliced into decision-shaped entries. One parked entry may graduate into several decisions, or none.
- **No new tracker adapters.** Chart projection rides the existing four (Linear, GitHub, GitLab, Jira) or degrades to local-only.
- **Spec prose must not trip destructive-command guards.** Chart bodies, decision records, and briefings are frequently piped through shells by drivers and skills. Documentation examples inside these artefacts must avoid literal destructive command strings, which guard packs match on sight regardless of context. This spec is itself a worked example: an earlier draft was blocked by dcg for quoting an uninstall command in prose.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `/flow-next:chart "<idea>"` produces a chart with a named `## Outcome`, an empty `## Decisions` ledger, at least one decision record, and unknowns recorded under `## Open Questions`; it resolves no decisions in that session.
- **R2:** Charting an idea that surfaces nothing to park terminates without creating a chart, and states that the effort is small enough to capture directly.
- **R3:** Every decision record carries exactly one type from `research | probe | eval | prototype | interview | task`, and the type is required at creation.
- **R4:** `flowctl chart frontier <id>` returns only open, unblocked, unclaimed decisions, dependency-ordered, and is the sole selection input for work mode.
- **R5:** Work mode claims a decision atomically before any work; a second session claiming the same decision fails with a non-zero exit and a distinguishable error.
- **R6:** Resolving a decision writes the answer to its record, closes it, and appends exactly one gist line with a link to `## Decisions`. The map body never restates the answer.
- **R7:** Resolving a decision graduates any newly-specifiable entry into decision records and removes that entry from `## Open Questions`, so no content exists in both places.
- **R8:** An attended decision (`prototype`, `interview`) reached in an unattended run terminates `CHART_VERDICT=NEEDS_HUMAN` without writing an answer.
- **R9:** Unattended decisions (`research`, `probe`, `eval`) may be dispatched in parallel within one session; attended decisions are limited to one per session.
- **R10:** `flowctl chart out-of-scope` closes a decision, writes a one-line reason under `## Boundaries`, and produces no entry under `## Decisions`.
- **R11:** `flowctl chart briefing <id>` refuses with a non-zero exit while the frontier or `## Open Questions` is non-empty, unless `--force` is passed.
- **R12:** The emitted briefing index contains the Outcome, every decision with gist and link, superseded decisions, all recorded assets, and the boundaries list; `/flow-next:capture` accepts a briefing as an input without transformation.
- **R13:** Chart writes no file under `.flow/specs/` and never mutates a spec's `ready` flag.
- **R14:** Every `flowctl chart` subcommand supports `--json` and emits schema-valid output.
- **R15:** Work mode terminates with exactly one `CHART_VERDICT=` line matching the documented grammar.
- **R16:** With `tracker.charts` enabled, a chart projects as a parent issue with decisions as children and native blocking edges; with it disabled or no tracker configured, all chart operations succeed local-only.
- **R17:** Every documented flag has a plain-language equivalent that reaches the same behavior.
- **R18:** Chart ids allocate through the same allocator as specs, and a chart and spec never share an id.
- **R19:** Docs ship with the skill: a `skills/chart.mdx` page on flow-next.dev, entries in **both** nav sources, a changelog entry, GLOSSARY terms (chart, decision record, D-ID, frontier, briefing package, supersession), and a cross-link from the prototype-driven-specs page.
- **R20:** No chart-authored artefact (chart body, decision record, briefing) emitted by the skill contains a literal destructive shell command string; the skill's own documentation examples use prose descriptions instead.
- **R21:** `flowctl chart resolve --supersedes <D>` flips the named decision to `superseded`, sets `superseded_by`, and rewrites its ledger line as struck-through with a pointer to the superseding D-ID. The superseded line and its record are never removed.
- **R22:** Supersession re-opens every open decision declaring `depends_on` on the superseded D-ID, clearing their claims and naming the superseding D-ID as the reason; `--keep-dependents` suppresses the re-open and records that judgment on the record. Either way the affected D-IDs are reported.
- **R23:** D-IDs are allocated sequentially from D1, are never renumbered and never reused, and removal or supersession leaves a gap.
- **R24:** `flowctl chart briefing` proposes a spec split with a one-line rationale per boundary and names any decision landing in more than one cluster as shared context, then requires confirmation before emitting. The default proposal is a single spec.
- **R25:** A confirmed multi-spec briefing emits one index plus one briefing per spec, each carrying the shared Outcome, its cluster's decisions, and their assets; `produced_specs[]` records the D-ID-to-spec mapping once capture runs.
- **R26:** Chart mode reports a session-cost estimate (unattended count, attended count, estimated sessions) before persisting, and refuses to persist past `chart.maxDecisions` (default 12) without `--force`, proposing a narrower Outcome or a split instead. `flowctl chart show` and `flowctl chart list` report remaining attended cost.

## Boundaries
<!-- scope: business -->

- **Not a project-management tool.** Chart tracks decisions in flight for one effort, then closes. It is not a roadmap, a portfolio view, or a backlog.
- **Not a replacement for `prospect` or `strategy`.** Chart starts from one idea that already exists.
- **Not a builder.** Only `task` decisions do anything, and only to unblock a decision. Charting an effort must not become a way to smuggle implementation past plan and review.
- **Not a spec author.** Output is a briefing; `capture` remains the only path into `.flow/specs/`.
- **No new review backends, trackers, or hosts.** Chart composes with what exists.
- **Autonomous end-to-end discovery is out of scope for v1.** Unattended decision types may be driven by a loop, but a chart that reaches only attended decisions parks. Fully autonomous discovery would require an agent to stand in for product judgment, which is the one thing the doctrine says it must not do.
- **Cross-chart decision reuse is out of scope for v1.** Citing a prior chart's D-ID as an answer is desirable and additive; it is not needed to ship.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Two independent pressures land on the same missing primitive.

**Field pressure.** In rollout conversations the pre-capture stage is where teams stall. The observed failure is not that people dislike specs; it is that they are asked to write one before the effort is knowable, produce a spec full of guesses, and then conclude that spec-first does not work. Meanwhile the discovery that *would* have made the spec good happens in meetings and evaporates. The same conversations produce the recurring ask for a surface where product, BA, and quality can participate without a repo checkout.

**Doctrine pressure.** flow-next now ships an explicit position: the spec is a ratchet not a gate, the spec is an output of discovery, and the way to get a good one is to let something real answer the question first. That doctrine currently has cookbook recipes and a strategy page, but no primitive that *structures* a discovery effort too large to hold in one session. Chart is the doctrine made executable, which is why its decision types are the route family verbatim rather than a fresh taxonomy.

The timing argument: the ideation edge was left deliberately open, and that was correct. Chart does not close it. It adds one composable primitive inside the open edge, whose output is a briefing package -- the same artefact a company-specific front door would emit. Teams that already have their own discovery process keep it and ignore chart.

### Implementation Tradeoffs
<!-- scope: technical -->

**Vocabulary is flow-next's own, deliberately.** `## Outcome`, `## Decisions`, `## Open Questions`, `## Boundaries`, D-IDs, frontier, claims, briefing package, and the `CHART_VERDICT` grammar are all either existing flow-next terms or direct analogues of them (`## Open Questions` and `## Boundaries` are spec sections the interview already writes to; D-IDs follow the R-ID discipline exactly; frontier is the word `/flow-next:work` already uses for the ready task set). A reader who knows a spec can read a chart cold, and the skill inherits conventions rather than teaching a parallel vocabulary.

**Files-first, tracker-optional.** Charts live in `.flow/` for the same reasons specs do: portable, greppable, diffable, no hosted dependency, and deleting the `.flow/` directory still uninstalls cleanly. Tracker projection is additive. The alternative (tracker as the store) was rejected: it would make discovery unavailable offline, tie the primitive to four vendor APIs, and invert projection-not-coordination.

**Decision types mirror the doctrine rather than inventing a taxonomy.** Rejected a generic decision type with free-form resolution. Typing the decision is what makes the route selectable and the attended/unattended boundary mechanical, and reusing the published route family means one concept is taught in one vocabulary across the strategy page, the cookbook, and the skill.

**One attended decision per session.** Rejected batching. The context-collapse failure mode is well-evidenced across the orchestration work, and a decision made at the tail of a long session is measurably worse than one made fresh. Unattended types are exempted because they return facts rather than consume judgment.

**Parked unknowns as a first-class section rather than pre-created stub decisions.** Rejected auto-slicing `## Open Questions` into stub records: one parked entry may graduate into several decisions or none, and stubs pollute the frontier with items nobody can act on. The state-it-vs-answer-it test is the cheapest reliable discriminator.

**Supersession over mutation.** Rejected editing a resolved decision in place, which is the obvious cheap fix and the wrong one: it destroys the record of what was tried, and silently invalidates anything that depended on the old answer. Immutable-plus-supersede matches the completed-spec-is-change-history rule already in the glossary, keeps reversals as evidence for the eventual `## Decision Context`, and makes the dependent cascade explicit rather than a thing a human has to remember. The cost is a heavier resolve path and a struck-through ledger; both are worth it, and a chart with visible reversals is more trustworthy than one that reads as if discovery went in a straight line.

**The spec split is decided at briefing time, not charting time.** Rejected declaring the split up front, because the boundaries worth splitting on are usually discovered *during* discovery, and a split guessed at charting time hardens exactly the guess the chart exists to avoid. Rejected also letting capture infer it silently, since a wrong split is expensive and invisible. Proposing with rationale and requiring confirmation reuses capture's read-back consent pattern, and the shared-context flag keeps one decision from becoming two divergent requirements.

**Cost reported before spent, with a ceiling.** Rejected leaving discovery cost implicit. The dominant cost is attended sessions, and a 20-decision chart is a quarter of discovery wearing one effort's clothes -- the failure mode is discovering that in week three. A charting-time refusal past `chart.maxDecisions` with a proposal to narrow the Outcome or split makes the size decision at the only point where it is cheap. The ceiling deliberately does not apply to later graduations, because a chart legitimately growing from what it learned is the system working.

**Named `chart`, not `map`.** `/flow-next:map` is already the clawpatch feature-map wrapper. `chart` reads as both noun and verb and does not collide.

**Deferred to a follow-up:** cross-chart decision reuse, chart templates for recurring discovery shapes, and a visual frontier renderer via the render-lens layer. All are additive and none block v1.

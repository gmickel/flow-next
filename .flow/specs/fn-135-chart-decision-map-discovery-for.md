# fn-135 chart: decision-map discovery for oversized ideas (pre-capture)

## Goal & Context
<!-- scope: business -->

Everything from `capture` onwards is heavily exercised and deliberately opinionated. The stage *before* capture is not. Field coaching keeps surfacing the same two-sided gap:

- `/flow-next:prospect` gives you a **ranked idea**. `/flow-next:capture` wants **intent it can write down**. Between them, for an effort that is genuinely large and genuinely foggy, there is nothing. Teams either capture too early (a spec full of `[inferred]` criteria that the interview then has to demolish) or hold a series of unstructured meetings whose output evaporates.
- The ideation edge is the most company-specific part of any delivery process, so the answer is not to bolt a fixed discovery ceremony onto the front. It is to ship a **composable** discovery primitive that produces a briefing package, which is exactly what the shipped [prototype-driven-specs](https://flow-next.dev/strategy/prototype-driven-specs/) doctrine tells people to bring their own front door for.

`/flow-next:chart` fills that gap. It takes **one loose idea that is too big for a single capture session and wrapped in unknowns**, and finds the route to it by resolving one decision at a time until the effort can be captured as one or more specs.

The unit of a chart is a **decision** -- a question whose resolution settles something, not a slice of a build. This is what separates chart from `plan`: plan decomposes work that is already understood; chart makes an effort understandable enough to be worth planning.

Chart is also where the evidence-first route family stops being prose and becomes executable. The doctrine says "let something real answer the question, then capture the answer", and names the routes: prototype, probe, reproduce, eval, bake-off, research, spike. A chart's decision types **are** those routes, so the doctrine page and the skill teach the same thing.

The interaction is **prompt-first**. The command and flags are deterministic escape hatches for automation and exact selection, not the product's primary interface. A person should be able to say what they are trying to reach, what they learned, what they want to try next, or what they already know enough to skip; the host agent translates that into chart operations, recommends the smallest useful next decision, and reads back any state-changing interpretation before persisting it.

### The adaptive discovery loop

Chart is intentionally not a complete discovery plan written up front. Its operating loop is:

1. **Re-anchor on the Outcome.** State what the effort is trying to make possible and what is currently known.
2. **Choose the next uncertainty.** Select one frontier decision whose answer most reduces uncertainty or unlocks other decisions.
3. **Take the smallest evidence route.** Research, probe, evaluate, prototype, interview, or perform the enabling task -- whichever can settle that decision with the least ceremony.
4. **Record what changed.** Resolve, supersede, park, or rule out the decision with its evidence and assets.
5. **Re-chart from the new state.** Recompute the frontier; add only decisions that became visible because of the answer; prune branches that no longer matter.
6. **Stop at the right boundary.** Continue while pre-build judgment remains; emit a briefing when nothing material remains to decide.

The route therefore adapts after every answer rather than pretending the initial map can predict the whole discovery effort. One decision is sized for one agent session. A decision may be analysis, evidence gathering, a throwaway artefact, or human judgment; it is never required to pass through a fixed sequence of route types.

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

### Where chart sits -- and when to skip it

The public pipeline must present chart as an **optional discovery on-ramp**, not a newly mandatory stage:

| Starting state | Smallest sufficient route |
|---|---|
| Looking for candidate investments across a domain | `prospect`, then choose `chart` only if the selected candidate remains too foggy to capture |
| One large idea, unclear boundaries, several consequential unknowns | `chart` -> briefing -> `capture` |
| One meaningful idea whose intent and boundaries can already be stated | Skip chart; go directly to `capture` or author the spec directly |
| Existing structured brief with resolved business and technical choices | Skip chart; `capture` the brief, then skip or narrow `interview` when the read-back exposes no material gaps |
| Tiny, local, low-risk change that fits one implementation context | Skip chart and the full spec pipeline; use the smallest direct change/review path appropriate to the repo |
| A valid spec with unresolved judgment questions | Use `interview`; do not reopen discovery as a chart unless the questions reveal that the effort itself is not yet specifiable |
| A ready spec whose work is understood | Use `plan`; chart is too late |
| Unsure which of these situations applies | Use `guide`, which must route using this matrix |

Chart never bypasses `capture`: its output is evidence for a spec, not a spec. The other stages remain composable under the existing menu-not-a-rail doctrine. Documentation must distinguish **optional because the signal is absent** from **skipped despite unresolved risk**; skipping a command never means skipping the evidence, consent, or review contract that command would have provided.

## Architecture & Data Models
<!-- scope: technical -->

### The chart object

A chart is git-native like a spec, and lives beside them:

- `.flow/charts/<chart-id>.md` -- the map body (below).
- `.flow/charts/<chart-id>.json` -- metadata sidecar: `id`, `title`, `outcome`, `status` (`open|done|abandoned`), `created`, `decisions[]`, `briefings[]`, `tracker` projection keys, `produced_specs[]`, and any audited force/break-claim events.

Chart ids share the repo prefix and allocator with specs (`<prefix>-<n>`) but carry a distinct kind so `flowctl list` can render them separately. This is one cross-kind allocation domain, not two counters: allocation scans specs and charts across the working tree, linked worktrees, and visible refs under one lock, then reserves the next id with no-clobber creation. `flowctl spec create` and `flowctl chart create` therefore cannot race into the same id.

The map body reuses spec section names wherever the meaning matches, so a reader who knows a spec can read a chart cold. It is an **index, not a store** -- a decision's detail lives in exactly one place, its own record, so the map gists and links but never restates:

```markdown
# <chart-id> <Title>

## Outcome
<What reaching the end of this chart looks like: the spec(s), the decision, or the
change this effort is finding its way to. One or two lines. Every session re-anchors
on it before choosing a decision.>

## Notes
<Domain. Skills every session should consult. Standing preferences for this effort.>
<Known facts carry citations or approved evidence references here. Acceptance-
criterion source tags do not apply to chart facts. A fact becomes a resolved D-ID
only when the chart actually asked and settled that question; importing background
does not fabricate decision history.>

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

### Three provenance lanes that must not collapse

Chart sits beside two provenance changes that deliberately own different surfaces:

1. **Chart decision provenance** is structural: D-ID, decision type, answer, evidence/assets, dependencies, supersession, and briefing membership. A briefing preserves those links and references; it does not convert them into trailing source tags.
2. **Acceptance-criterion author provenance** uses the existing `[user] | [paraphrase] | [inferred] | [strategy:<track>]` trailing tags. Capture already applies them to criteria it newly writes; fn-147 extends the same semantics to criteria interview newly writes. These tags answer *who grounded this criterion*, not *how strong the supporting evidence is*. A criterion derived from a resolved unattended D-ID is therefore not automatically `[user]`.
3. **Verified-versus-inferred technical facts and decisions** are the subject of fn-148's preregistered eval. fn-135 adds no chart-level `[verified]`/`[inferred]` grammar and makes no template claim ahead of that result. If fn-148 later lands human-approved guidance, fn-135 consumes the landed wording without widening it; a null or inconclusive result changes nothing here.

This separation is load-bearing. It preserves fn-147's append-only rule (never retag a criterion authored by an earlier pass), keeps D-ID evidence navigable, and avoids contaminating fn-148's baseline by shipping its experimental intervention through chart first.

### The decision record

Each decision is a child record of the chart, one per file under `.flow/charts/<chart-id>/<n>.md` with a JSON sidecar, mirroring the spec/task split so existing readers, the tracker projector, and `flowctl anchor` need no new transport.

Body is deliberately minimal -- the question, nothing else:

```markdown
## Question
<what this decision settles>
```

Sidecar fields: `id` (canonical external form `<chart-id>.D<n>`), `chart`, `title`, `type`, `attendance` (`attended|unattended`), `status` (`open|resolved|superseded|out-of-scope`), `blocked_by[]`, `depends_on[]`, `supersedes[]`, `superseded_by`, `claimed_by`, `claimed_at`, `claim_note`, `assets[]` (branch refs, repository-relative evidence paths, tracker URLs), `answer` (written on resolution), and append-only transition notes. D-IDs are chart-local; every parser canonicalizes the full chart-qualified form before I/O, while human output always pairs it with the decision title and record link.

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
| `task` | explicitly either | Manual work that unblocks a *decision* (provision access, obtain credentials, move data so its shape can be seen). The one type that does rather than decides; earns its place by unblocking |

Attended types never resolve without the human's side of the exchange. An agent that answers its own `prototype` or `interview` decision has broken the contract, and this is an explicit gate, not a convention. This is the same consent boundary the autonomy loops hold, expressed one stage earlier.

`attendance` is derived and validated for five types (`research|probe|eval` -> unattended; `prototype|interview` -> attended). A `task` decision must state it explicitly at creation because “obtain a machine-readable export” and “have the account owner approve access” carry different autonomy and cost. Cost and unattended gates read `attendance`, never infer from prose.

### Frontier, parked questions, and scope

- **Blocking** uses `blocked_by[]`: the named decision must close before this decision is actionable. **Premise dependence** uses `depends_on[]`: this decision's conclusion relies on the named answer and must be re-evaluated if that premise is superseded. The arrays are not aliases, though the same D-ID may appear in both. Missing targets, self-edges, duplicates, and cycles are rejected atomically before either file changes. When a chart is projected to a tracker, only `blocked_by[]` becomes the native blocking relation; `depends_on[]` remains local provenance unless an adapter has a lossless distinct relation.
- **Frontier** = open, unblocked, unclaimed decisions -- the same word and the same shape `/flow-next:work` already uses for the ready task frontier. `flowctl chart frontier <chart-id>` returns it.
- **`## Open Questions`** holds deliberate incompleteness: in-scope unknowns you can tell are coming but cannot yet phrase sharply. The test for parked-vs-decision is whether the question can be **stated** precisely now, not whether it can be **answered** now. A sharp but blocked question is a decision record. A vague one parks. Resolving a decision graduates whatever it made specifiable into fresh decision records, and clears that entry from `## Open Questions` so it lives in exactly one place.
- **`## Boundaries`** is a scoping act, not a route step. A decision exposed as sitting past the Outcome is closed with a one-line reason under `## Boundaries`, and stays out of `## Decisions`, which records the route actually walked.

An empty frontier is not completion by itself. A chart is briefable only when it has no `open` decisions (blocked, unblocked, or claimed) and no parked Open Questions. All-blocked and all-claimed charts report why they are stuck rather than pretending they are done.

### Claims, transitions, and crash recovery

The deterministic state machine permits only:

- `open -> resolved | superseded | out-of-scope`;
- `resolved -> superseded`;
- a premise-invalidated `open` decision remains `open` but receives a transition note and loses its claim;
- reopening a resolved dependent creates a replacement D-ID that supersedes the old conclusion rather than mutating resolved history.

Claiming does not change `status`; it writes `claimed_by` and `claimed_at` under the chart lock. A worker that stops normally releases an unresolved claim with an audited note. A crash leaves a visible claim. `flowctl chart release-claim` lets the owner release it; `--break-stale --reason` is allowed only after `chart.claimStaleAfter` and records actor, prior owner, age, and reason. No silent expiry or takeover.

Every mutation locks the chart resource and validates the complete intended state before publication. Chart Markdown, chart JSON, decision Markdown/JSON, the ledger, and any dependent cascade are one recoverable transaction: no-clobber initial creates, temporary staged replacements for updates, atomic rename, and rollback to the pre-call state on failure. Locks coordinate linked worktrees on one filesystem; separate clones reconcile through git and may surface ordinary merge conflicts, never claim cross-clone exclusivity.

Every chart JSON response uses a versioned envelope. Success is `{success:true,schema_version:1,command,result}`. Failure is `{success:false,schema_version:1,command,error:{class,code,message,details}}`, with `class` from `not_found | conflict | invalid_state | invalid_graph | stale_claim | validation | io`. This keeps the repo's existing `success` convention rather than inventing `ok`. Human diagnostics go to stderr; stdout stays machine-parseable under `--json`. Exact per-command result fixtures are part of the API contract.

Multi-file chart mutation is crash-recoverable, not merely exception-safe. A write-ahead journal under `.flow/charts/.transactions/` records the pre-state fingerprints, complete intended mutation set, and publication phase; file and directory metadata is flushed before replacement. Every chart command recovers an incomplete journal under the same resource lock before reading state, deterministically rolling forward a fully staged transaction or restoring the recorded pre-state. The allocator/store foundation also moves `spec create` onto the same cross-kind allocation lock; chart must not cite a rollback guarantee the existing spec writer does not yet have.

### Parked-question and graph mutation APIs

The skill never edits chart Markdown or sidecars directly. Open Questions and post-create graph wiring have deterministic operations:

- `park-question` adds one normalized question with a stable question key; identical retries are no-ops.
- `remove-question` removes by key and fails if absent unless the identical enclosing graduation transaction already committed.
- `wire-decision` validates and atomically replaces the target decision's `blocked_by[]` and `depends_on[]`.
- `resolve --graduation-file <json>` performs one transaction containing the answer, newly visible decision creates/wiring, and parked-question removals. It allocates all new D-IDs, validates the resulting graph, and commits all-or-nothing.

This is how chart mode persists initial fog and how work mode enforces “record once, then graduate” without bypassing the store.

### Supersession: when a later decision invalidates an earlier one

Resolved decisions are **immutable**, on the same principle as a completed spec: they are change history, not a wiki. A later finding never edits or deletes an earlier answer. It supersedes it.

`flowctl chart resolve <id>.<n> --supersedes D3` does four things atomically:

1. Writes the new answer and closes the new decision normally.
2. Flips `D3.status` to `superseded` and sets `D3.superseded_by`.
3. Rewrites D3's ledger line as struck-through with a pointer to the superseding D-ID. The line is **never removed** -- the route actually walked includes its wrong turns, and deleting them invites the same wrong turn twice.
4. Walks the direct and transitive `depends_on` closure. Open dependents stay open, lose claims, and receive a premise-invalidated note. Resolved dependents are preserved and superseded by fresh replacement D-IDs carrying the same question and an explicit re-evaluation reason. `--keep-dependents` suppresses that cascade when the dependency was incidental, and records that judgment on the new and affected records.

The briefing carries superseded decisions in their own section. They are evidence: they tell whoever reads the spec later which alternatives were tried and abandoned during discovery, which is exactly the material `## Decision Context` wants.

### Exit: the briefing package, and the spec split

A chart is done when no open decision remains and `## Open Questions` is empty.

**A chart may produce more than one spec.** A large effort routinely splits along boundaries only discovered *during* discovery, so the split is decided at briefing time rather than guessed at charting time. `flowctl chart briefing <id>`:

1. Clusters the resolved decisions and **proposes** N spec boundaries with a one-line rationale for each, and names any decision that lands in more than one cluster as **shared context** rather than a duplicated requirement.
2. Presents the proposal for confirmation before writing anything, matching capture's read-back consent pattern. The human may merge, split further, or override.
3. Emits `.flow/charts/<id>-briefing.md` as the index (Outcome, the full ledger, superseded decisions, boundaries) plus `.flow/charts/<id>-briefing-<k>.md` per proposed spec, each carrying the shared Outcome, the decisions in its cluster, and their assets.

Default is **N=1**; a split is only proposed when the decision clusters are genuinely disjoint. Clustering and confirmation are agent judgments owned by the chart skill. `flowctl` only validates and emits a confirmed proposal file; it never pretends a deterministic command obtained consent.

Briefings are immutable and versioned (`B1`, `B2`, ...). A forced briefing is marked `draft`, lists every unresolved/claimed/parked item, and leaves the chart `open`; it is never silently capture-ready. Capture ingests a briefing as attributable evidence, preserving its chart id, B-ID, cluster, D-ID links, and approved asset references, then applies its normal read-back and source tags only to acceptance criteria it newly authors. Declining the read-back changes neither chart nor handoff state.

Draft or stale briefings are refused for ordinary capture. An explicit override must identify the unresolved or invalidated decisions, read back the risk, and still cannot promote a forced draft to a final briefing. Shared-context D-IDs may be cited by more than one proposed spec, but capture must not duplicate them into acceptance requirements unless each target spec independently needs that guarantee.

After successful spec creation, capture calls an idempotent chart link operation with the briefing id, cluster key, spec id, and D-ID set. The handoff has a stable retry identity and recoverable journal across `spec create` / `spec set-plan` / `chart link-spec`: a process interruption after spec creation must discover and link the existing spec rather than create a duplicate. Partial multi-spec capture records only successful links and remains resumable; a declined or failed cluster does not roll back successful siblings. A later supersession marks affected briefing/spec links stale but does not rewrite them.

Publishing the first non-draft briefing transitions `open -> done`. A done chart is immutable to add/wire/resolve/scope operations. `chart reopen --reason` explicitly transitions `done|abandoned -> open`, records who/why, and marks existing briefings plus affected spec links stale before new decisions or supersession are accepted. Re-briefing computes a fingerprint over chart revision plus normalized confirmed proposal: an identical retry returns the existing B-ID; a changed proposal or later chart revision allocates the next B-ID. `abandoned` is otherwise terminal.

### Cost is reported before it is spent

Discovery cost is dominated by **attended** decisions, because each one is a session with a human in it. Chart mode therefore ends with an estimate before it persists anything:

```
9 decisions: 5 unattended (parallel, ~1 session), 4 attended (~4 sessions).
Estimated 4-5 working sessions with you.
```

`flowctl chart show` carries the same line for the remaining frontier, so the outstanding human cost is visible at a glance rather than discovered three weeks in. Initial persistence is one guarded transaction: the skill supplies the proposed titled decisions and parked questions in an initial-map file, so `flowctl` can enforce the ceiling before any chart file exists. An over-ceiling override requires the prompt layer to show the warning and read back consent first; `--force-size --reason` then records actor, configured ceiling, proposed count, timestamp, and reason in the create transaction.

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

The skill must also understand conversational steering without making the user translate it into chart vocabulary. Illustrative, native examples:

- "This still feels too broad to write a spec. Help me find the first thing worth deciding."
- "We already know the storage choice; don't research it again. What uncertainty does that remove?"
- "Use the cheapest real-world check that would tell us whether this architecture is viable."
- "That prototype changed the direction. Record the old assumption and redraw what remains."
- "I think this is clear enough now. Show me what would go into one spec versus two."
- "Don't build anything yet; I only want the decisions and evidence needed for capture."

On every prompt, the host agent infers the intended operation and decision type from context. It asks a blocking question only where two interpretations would materially change the chart, cost, or consent boundary. Exact commands remain documented for scripting, debugging, and autonomous drivers, but normal users should not need to memorize them.

### flowctl

| Command | Contract |
|---|---|
| `flowctl chart create --title <t> --outcome <o> --initial-map-file <f> [--force-size --reason <r>]` | Validates initial titled decisions/parked questions, enforces the size ceiling before allocation, then atomically creates the chart; override is audited |
| `flowctl chart show <id>` | Map body + counts (resolved / open / blocked / parked) + remaining attended-session estimate |
| `flowctl chart frontier <id>` | Open, unblocked, unclaimed decisions, dependency-ordered |
| `flowctl chart add-decision <id> --title <t> --type <t> [--attendance <a>] --body-file <f> [--blocked-by <D,...>] [--depends-on <D,...>]` | Allocates the next D-ID; attendance is required only for `task` |
| `flowctl chart park-question <id> --body-file <f>` | Adds a normalized parked question and returns its stable key |
| `flowctl chart remove-question <id> --question <Q>` | Removes a parked question idempotently within a committed graduation |
| `flowctl chart wire-decision <id>.<D> [--blocked-by <D,...>] [--depends-on <D,...>]` | Atomically replaces validated graph edges after two-pass creation |
| `flowctl chart claim <id>.<D>` | Atomic claim; refuses an already-claimed decision |
| `flowctl chart release-claim <id>.<D> [--break-stale --reason <r>]` | Owner release or audited stale-claim recovery |
| `flowctl chart resolve <id>.<D> --answer-file <f> [--assets <json>] [--graduation-file <json>] [--supersedes <D,...>] [--keep-dependents]` | Records the safe answer, closes it, appends the ledger line, and atomically graduates/removes parked questions |
| `flowctl chart out-of-scope <id>.<D> --reason <r>` | Closes without a decision; writes the `## Boundaries` line |
| `flowctl chart briefing <id> --proposal-file <f> [--force]` | Validates an agent-confirmed split proposal, then emits an immutable briefing version; forced output is draft-only |
| `flowctl chart link-spec <id> --briefing <B> --spec <S> --decisions <D,...>` | Idempotently records a successful capture result |
| `flowctl chart reopen <id> --reason <r>` | Reopens done/abandoned discovery and marks previous briefings/spec links stale |
| `flowctl chart list` | Open charts with progress and remaining attended cost |

All commands take `--json`. Machine-readable output is the contract for autonomous drivers.

### Verdict grammar

Each work invocation selects and claims exactly one decision and terminates with one greppable line, matching the pilot convention so host `/loop` and `/goal` drivers can drive discovery the same way they drive the build loop:

```
CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="<one line>"
```

`NEEDS_HUMAN` is the terminal verdict for an attended decision reached by an unattended driver -- the loop parks it rather than self-answering.

Parallelism means parallel **invocations**, never a batch tick: the host may dispatch independent unattended frontier decisions concurrently, and each owns one claim, progress stream, recovery path, and verdict. A single invocation never aggregates mixed outcomes or claims a set, so the one-decision verdict grammar stays complete. Crashed invocations remain visible through their audited claims; stale recovery follows the explicit claim contract.

## Edge Cases & Constraints
<!-- scope: technical -->

- **One decision per invocation.** Resolving more than one attended decision per session reintroduces the context collapse the chart exists to prevent. Independent unattended types (`research`, `probe`, `eval`, or unattended `task`) may fan out only as separate invocations, each with its own claim and verdict.
- **No fixed route sequence.** A chart does not require research before prototype, interview before eval, or any other phase order. Each tick selects the smallest route justified by the current frontier and then re-charts. Documentation may show example journeys, but must not turn them into a canonical checklist.
- **Prompting is the primary control surface.** Flags provide precision and automation; they must not become required vocabulary in onboarding, guide output, or examples. Free-form steering reaches the same guarded operations.
- **Session-sized decisions.** Every selected decision must fit one agent context. If it does not, work mode splits the question before dispatch rather than asking an agent to plan, research, prototype, and decide an entire workstream in one session.
- **Charting resolves nothing.** Chart mode ends after the map, the first decision records, and the cost estimate exist. A charting session that starts answering its own decisions has skipped the human's scoping act.
- **The agent never answers an attended decision.** Hard gate, not guidance. A `prototype` or `interview` decision resolved inside an unattended run is a contract violation and must terminate `NEEDS_HUMAN`.
- **Chart never writes a spec.** It hands a briefing to `capture`. Letting chart author specs directly would let discovery content bypass capture's acceptance-criterion source-tagging and read-back, which is exactly the guarantee the ratchet depends on.
- **Chart never sets `ready`.** Promotion stays a human act, unchanged.
- **Charts are not required.** A small, well-understood effort goes straight to `capture`. Reaching for a chart on a two-day feature is the same error as running a full interview on a one-line fix. `/flow-next:chart` on an idea with nothing parked must say so and stop rather than manufacture decisions.
- **Charts have a size ceiling.** Past `chart.maxDecisions` (default 12) at charting time, chart refuses to persist and proposes either narrowing the Outcome or splitting into two charts, because a 20-decision chart is a quarter of discovery masquerading as one effort. `--force-size --reason` overrides only after prompt-layer warning/read-back and records actor, configured ceiling, proposed count, timestamp, and reason. The ceiling is a charting-time guard only; decisions graduated later from `## Open Questions` may legitimately carry a chart past it.
- **A superseded decision is never deleted.** Its ledger line is struck through, its record stays readable, and it appears in the briefing under its own heading. Reversals are the most valuable thing a chart learns.
- **Supersession cascades are reported, never silent.** Re-opening dependents clears their claims, so a session holding one must re-claim; the re-open reason names the superseding D-ID.
- **Abandoned charts.** An effort killed mid-discovery closes `abandoned` with its decisions intact. The decisions were paid for and stay searchable; a future chart may cite them.
- **Concurrency.** Multiple sessions may work one chart. Claims are atomic and checked before any work; a stale claim (configurable age) can be broken with a recorded note.
- **`## Open Questions` is not a backlog.** It must not be pre-sliced into decision-shaped entries. One parked entry may graduate into several decisions, or none.
- **No new tracker adapters.** Chart projection rides the existing four (Linear, GitHub, GitLab, Jira) or degrades to local-only.
- **Unsafe evidence stays referenced, not copied.** If an answer contains an obvious secret or a literal guard-triggering destructive command, chart refuses to embed it. The source remains at a repository-relative evidence path or approved HTTPS reference; the decision stores a safe redacted/escaped summary and link. This applies to answer bodies, assets, normal briefings, and forced drafts. Never silently strip bytes from the cited source.
- **Do not overload source tags.** Chart facts, decisions, assets, D-ID records, and briefing evidence do not use the acceptance-criterion trailing-tag grammar. Capture and interview tag only criteria they newly author, and never retag an existing bullet.
- **Do not preempt fn-148.** No verified/inferred fact or decision grammar ships through chart unless fn-148 returns CONFIRMED, the human approves the ready-to-apply diff, and that guidance has landed. Null, inconclusive, or merely planned outcomes add nothing.
- **Handoff retries are identity-safe.** A crash after a spec is created but before the chart link is recorded must not produce a second spec on retry. Draft/stale briefing admission and partial multi-spec recovery fail visibly, never by guessing from titles.
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
- **R9:** Independent unattended decisions may be dispatched as separate parallel work invocations, each claiming exactly one D-ID and emitting its own verdict; no batch invocation aggregates mixed outcomes. Attended decisions remain one per session.
- **R10:** `flowctl chart out-of-scope` closes a decision, writes a one-line reason under `## Boundaries`, and produces no entry under `## Decisions`.
- **R11:** `flowctl chart briefing <id>` refuses with a non-zero exit while any open decision (including blocked or claimed decisions) or `## Open Questions` remains, unless `--force` is passed; forced output is visibly draft-only and leaves the chart open.
- **R12:** The emitted briefing index contains the Outcome, every decision with title, gist and link, superseded decisions, all recorded assets, and the boundaries list; `/flow-next:capture` preserves its chart/B-ID/cluster/D-ID evidence references, then applies normal read-back consent and source tags only to acceptance criteria capture newly authors.
- **R13:** Chart writes no file under `.flow/specs/` and never mutates a spec's `ready` flag.
- **R14:** Every `flowctl chart` subcommand supports `--json` and emits an exact fixture-validated v1 envelope using `success`, `schema_version`, `command`, and a command-specific `result` or structured `error`.
- **R15:** Work mode terminates with exactly one `CHART_VERDICT=` line matching the documented grammar.
- **R16:** With `tracker.charts` enabled, a chart projects as a parent issue with decisions as children and native blocking edges; with it disabled or no tracker configured, all chart operations succeed local-only.
- **R17:** Every documented behavioral flag has a plain-language equivalent that reaches the same behavior; transport-only controls such as `--json` remain documented for automation and are not forced into conversation.
- **R18:** Chart ids allocate through the same allocator as specs, and a chart and spec never share an id.
- **R19:** Docs ship with the skill as a pipeline-level change, not one isolated skill page: a `skills/chart.mdx` page on flow-next.dev; entries in **both** nav sources; repo and docs-site `## Unreleased` changelog entries; GLOSSARY terms (chart, decision record, D-ID, frontier, briefing package, supersession); and updates to README, the command/skills index, architecture/lifecycle docs, `guide`, menu-not-a-rail, prototype-driven-specs, cookbook, first-run/when-to-use guidance, teams, orchestration/autonomy guidance, and any pipeline diagram or command inventory that presents the idea-to-PR route. Platform docs are updated wherever host behavior differs. No version bump is made as part of this spec.
- **R20:** No chart-authored artefact (chart body, decision record, briefing) emitted by the skill contains a literal destructive shell command string; the skill's own documentation examples use prose descriptions instead.
- **R21:** `flowctl chart resolve --supersedes <D>` flips the named decision to `superseded`, sets `superseded_by`, and rewrites its ledger line as struck-through with a pointer to the superseding D-ID. The superseded line and its record are never removed.
- **R22:** Supersession traverses the direct and transitive `depends_on` closure: open dependents lose claims and receive a premise-invalidated note; resolved dependents remain immutable and gain replacement D-IDs for re-evaluation. `--keep-dependents` suppresses the cascade and records that judgment. Either way every affected D-ID is reported.
- **R23:** D-IDs are allocated sequentially from D1, are never renumbered and never reused, and removal or supersession leaves a gap.
- **R24:** `flowctl chart briefing` proposes a spec split with a one-line rationale per boundary and names any decision landing in more than one cluster as shared context, then requires confirmation before emitting. The default proposal is a single spec.
- **R25:** A confirmed multi-spec briefing emits one index plus one briefing per spec, each carrying the shared Outcome, its cluster's decisions, and their assets; `produced_specs[]` records the D-ID-to-spec mapping once capture runs.
- **R26:** Chart mode reports a session-cost estimate (unattended count, attended count, estimated sessions) before persisting, and `chart create` refuses the initial-map file past `chart.maxDecisions` (default 12) without `--force-size --reason`, proposing a narrower Outcome or split first. The skill may pass that override only after warning/read-back; the create transaction records actor, configured ceiling, proposed count, timestamp, and reason. `flowctl chart show` and `flowctl chart list` report remaining attended cost.
- **R27:** The primary chart workflow is prompt-first: free-form statements of outcome, new evidence, desired next move, known answers, skips, reversals, and briefing intent reach the correct guarded chart operation without requiring command syntax or decision-type vocabulary.
- **R28:** After every resolved, superseded, or out-of-scope decision, work mode recomputes the frontier and proposes the next smallest uncertainty from the new state; it does not execute a frozen up-front sequence. Newly visible decisions are added only after the answer that exposed them.
- **R29:** Every selected decision fits one agent session. Oversized decisions are split before claim/dispatch, while unattended decisions that are genuinely independent may still fan out in parallel.
- **R30:** The shipped guide and public when-to-use material contain one consistent smallest-sufficient-workflow matrix covering direct change, prospect, chart, capture/direct spec authoring, interview, plan, work, and the review/ship path, including explicit conditions for skipping or narrowing each pre-build stage.
- **R31:** Adjacent skill surfaces (`prospect`, `guide`, `capture`, `interview`, `plan`, `pilot`) recognize chart at their handover boundaries: they recommend it only for a single oversized/foggy idea, accept its outputs where appropriate, and do not manufacture a chart for clear or already-ready work.
- **R32:** Documentation examples demonstrate at least four materially different adaptive journeys -- including a route that skips chart, a research-led chart, a prototype-led reversal with supersession, and a chart that splits into multiple specs -- without presenting any one journey as the mandatory phase order.
- **R33:** Exact flags remain fully documented for scripting and automation, but onboarding, the chart skill page, and `guide` lead with natural-language prompting. Every flag example has a semantically equivalent conversational example, and the examples are authored in flow-next's own chart vocabulary.
- **R34:** A docs inventory test or maintained assertion covers every canonical pipeline/when-to-use surface named by R19 and fails when chart is absent from a route where it belongs or presented as mandatory. Generated Codex copies are updated through `sync-codex.sh` twice and remain byte-idempotent.
- **R35:** Chart creation builds only the first visible frontier, breadth-first from the Outcome; it does not precompute a complete route. Independent unattended evidence routes may be offered for parallel dispatch, while the charting session resolves none of them.
- **R36:** Map, list, frontier, verdict, and guide output always pair a human-readable decision title with its D-ID and record link; no normal human-facing surface presents an unexplained wall of bare identifiers.
- **R37:** `flowctl` loads the chart map and compact decision metadata for navigation, then loads full decision answers/assets only for the selected operation or briefing. Status and frontier commands do not flood the host context with every record body.
- **R38:** Graph mutation rejects missing D-IDs, self-edges, duplicates, and cycles before writing; `blocked_by[]` alone controls readiness while `depends_on[]` alone controls premise-invalidating supersession cascades.
- **R39:** Stale claims are never silently expired. Owner release and age-gated break-claim operations are audited, distinguish conflict from stale-claim errors, and leave no partial chart/decision mutation after failure.
- **R40:** Chart/decision create, resolve, scope, supersession, and briefing publication are recoverable transactions across paired Markdown/JSON and the ledger; injected write failures prove rollback/no-clobber behavior.
- **R41:** Briefings are immutable/versioned. Capture decline and partial multi-spec capture leave the chart resumable; successful D-ID-to-spec links are idempotent; later supersession marks affected links stale without rewriting history.
- **R42:** Tracker projection uses the post-fn-141 lifecycle facade and a local provenance ledger. Remote partial success is reconcile-safe and idempotent; unsupported hierarchy/relation capabilities degrade explicitly without making remote state canonical or blocking local chart work.
- **R43:** Every decision has a title and mechanically validated attendance. Five decision types derive attendance; `task` requires it explicitly. Cost estimates and unattended gates use the stored field.
- **R44:** Park, remove, wire, and resolve-with-graduation operations are deterministic, idempotent, graph-validating transactions; the skill never edits Open Questions, edges, or graduated decisions directly.
- **R45:** The first non-draft briefing sets the chart to done. Later discovery requires an audited reopen that stales prior briefing/spec links. Identical briefing fingerprints reuse a B-ID; changed proposal or chart revision allocates the next B-ID.
- **R46:** Parallel unattended work is one invocation per D-ID with one claim and one verdict. Scenario tests cover crash/stale-claim recovery and demonstrate that no batch/mixed-result grammar exists.
- **R47:** Prompt-first behavior is exercised by a structured scenario/eval harness, not static prose checks alone: known facts, ambiguous steering/read-back, reversal, attended gating, adaptive frontier growth, guide routing, skip-chart, and exact terminal verdicts.
- **R48:** Unsafe or secret-bearing evidence is preserved by reference with a safe display summary; emitted chart, answer, briefing, and draft artifacts never copy literal guard-triggering commands or credentials.
- **R49:** Chart decision provenance and acceptance-criterion author provenance remain distinct: briefings preserve D-ID/evidence links, capture and interview use the settled four-tag grammar only on criteria each pass newly writes, existing criteria are never retagged, and untagged remains unknown rather than user-grounded.
- **R50:** Capture handoff is retry-safe and admission-aware: draft/stale briefings fail closed absent explicit risk read-back, shared-context D-IDs do not become duplicated requirements by default, and interruption between spec creation and `chart link-spec` resumes against the existing B-ID/cluster/spec identity without creating a duplicate.
- **R51:** fn-135 does not define verified/inferred marking for chart facts or decisions. Each overlapping implementation/docs task re-anchors on fn-148's final recorded outcome and consumes only human-approved guidance that has actually landed; NOT CONFIRMED or INCONCLUSIVE produces no chart contract or documentation claim.

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

**Prompt-first over command-first.** Rejected making users learn a chart subcommand vocabulary before they can discover anything. Exact commands are valuable deterministic plumbing, but the host agent already understands goals, evidence, reversals, and requests to skip known ground. The skill therefore treats natural-language steering as the normal interface and commands as the explicit automation/debugging interface. Read-back consent and hard attended-decision boundaries make this freedom safe.

**Adaptive loop over a discovery phase plan.** Rejected decomposing the whole chart into a fixed research -> interview -> prototype sequence at creation time. The next useful decision depends on the previous answer, and predicting the full route recreates plan-at-the-wrong-altitude. Chart sketches only the visible frontier, resolves one session-sized uncertainty, then redraws. It adopts the valuable phase-light behavior without discarding flow-next's durable decisions, evidence, consent, and briefing handover.

**Files-first, tracker-optional.** Charts live in `.flow/` for the same reasons specs do: portable, greppable, diffable, no hosted dependency, and deleting the `.flow/` directory still uninstalls cleanly. Tracker projection is additive. The alternative (tracker as the store) was rejected: it would make discovery unavailable offline, tie the primitive to four vendor APIs, and invert projection-not-coordination.

**Decision types mirror the doctrine rather than inventing a taxonomy.** Rejected a generic decision type with free-form resolution. Typing the decision is what makes the route selectable and the attended/unattended boundary mechanical, and reusing the published route family means one concept is taught in one vocabulary across the strategy page, the cookbook, and the skill.

**One attended decision per session.** Rejected batching. The context-collapse failure mode is well-evidenced across the orchestration work, and a decision made at the tail of a long session is measurably worse than one made fresh. Unattended types are exempted because they return facts rather than consume judgment.

**Parked unknowns as a first-class section rather than pre-created stub decisions.** Rejected auto-slicing `## Open Questions` into stub records: one parked entry may graduate into several decisions or none, and stubs pollute the frontier with items nobody can act on. The state-it-vs-answer-it test is the cheapest reliable discriminator.

**Supersession over mutation.** Rejected editing a resolved decision in place, which is the obvious cheap fix and the wrong one: it destroys the record of what was tried, and silently invalidates anything that depended on the old answer. Immutable-plus-supersede matches the completed-spec-is-change-history rule already in the glossary, keeps reversals as evidence for the eventual `## Decision Context`, and makes the dependent cascade explicit rather than a thing a human has to remember. The cost is a heavier resolve path and a struck-through ledger; both are worth it, and a chart with visible reversals is more trustworthy than one that reads as if discovery went in a straight line.

**The spec split is decided at briefing time, not charting time.** Rejected declaring the split up front, because the boundaries worth splitting on are usually discovered *during* discovery, and a split guessed at charting time hardens exactly the guess the chart exists to avoid. Rejected also letting capture infer it silently, since a wrong split is expensive and invisible. Proposing with rationale and requiring confirmation reuses capture's read-back consent pattern, and the shared-context flag keeps one decision from becoming two divergent requirements.

**Cost reported before spent, with a ceiling.** Rejected leaving discovery cost implicit. The dominant cost is attended sessions, and a 20-decision chart is a quarter of discovery wearing one effort's clothes -- the failure mode is discovering that in week three. A charting-time refusal past `chart.maxDecisions` with a proposal to narrow the Outcome or split makes the size decision at the only point where it is cheap. The ceiling deliberately does not apply to later graduations, because a chart legitimately growing from what it learned is the system working.

**Named `chart`, not `map`.** `/flow-next:map` is already the clawpatch feature-map wrapper. `chart` reads as both noun and verb and does not collide.

**Documentation is part of the feature.** Rejected treating chart as one new command page. It changes the mental model of the full pipeline: when discovery happens, when capture is premature, when chart is waste, and which later stages can be skipped or narrowed because equivalent evidence already exists. The implementation must update every canonical when-to-run and pipeline-routing surface together, with an assertion that prevents one property from silently reverting to a rigid conveyor.

**Provenance lanes stay separate.** fn-147 makes acceptance-criterion author tags consistent across capture and interview; chart consumes that settled behavior but does not make briefings or decision facts tag writers. fn-148 is research into a different prose demand for technical facts and inference-backed decisions. Reusing `[inferred]` for both would make one token answer two questions and would preempt the eval. D-ID/evidence links therefore remain structural, criterion tags remain author provenance, and any verified/inferred fact guidance is adopted only from a confirmed, human-approved fn-148 outcome.

**Coordination is not dependency.** fn-135 does not require fn-147 behavior to build its chart store or capture handoff, and fn-148 may correctly close with no product change. Neither belongs in fn-135's spec dependency DAG. The affected tasks must nevertheless re-read the landed fn-147 prompt/docs changes and fn-148 closeout before editing shared files, preserve both projects' existing `## Unreleased` entries, and resolve same-file changes additively rather than replacing them.

**The guide/router ships here.** The approved fn-67 routing scope never produced an implementation task or a shipped `/flow-next:guide` surface, while R30/R31 require one consistent router. This spec absorbs that settled scope rather than depending on an absent command: implement the small prompt-first guide, give it the smallest-sufficient-workflow matrix, and keep it pure routing rather than a new delivery stage.

**Tracker work waits for fn-141.** Chart projection must enter through the deterministic lifecycle facade after the tracker prose teardown, not recreate adapter choreography inside a new skill. fn-135 therefore depends on fn-141; the chart task adds its locator, hierarchy, relation, provenance, and reconcile contracts only after that caller surface is stable.

**Deferred to a follow-up:** cross-chart decision reuse, chart templates for recurring discovery shapes, and a visual frontier renderer via the render-lens layer. All are additive and none block v1.

## Strategy Alignment
<!-- scope: both -->

- **Spec-driven team patterns:** chart creates a durable pre-spec decision handover so product, quality, research, and engineering can contribute evidence without turning meetings or tracker comments into the source of truth.
- **Ralph autonomous mode:** unattended evidence routes can advance under a loop, but `NEEDS_HUMAN` makes the product-judgment boundary machine-checkable and terminal.
- **Cross-platform parity:** the canonical Claude-native skill, generated Codex mirror, and portable-host fallbacks follow the existing roster and sync discipline; no host gets a separate chart implementation.
- **Self-improving through normal work:** immutable reversals, linked evidence, and briefing-to-Decision-Context provenance preserve what discovery learned instead of discarding the false starts that prevent repetition.
- **Menu, not rail:** chart strengthens the pipeline only if it remains an optional high-fog route. Guide/docs tests must prevent it from becoming a universal new phase or inflating the quick-start path.

## Early Proof Point
<!-- scope: technical -->

Before the public skill/docs sweep, prove the riskiest lifecycle as a focused deterministic harness:

1. concurrent spec/chart allocation and concurrent decision claim;
2. failed paired-file/ledger publication rolls back cleanly;
3. blocked-only and claimed-only charts cannot brief;
4. missing/self/duplicate/cyclic edges are rejected;
5. direct and transitive supersession preserve old conclusions and create the right replacement work;
6. stale-claim release/break is audited;
7. briefing re-run is versioned/idempotent, while capture decline and partial multi-spec linking stay resumable;
8. one post-fn-141 tracker projection proves local-only, partial-remote reconcile, and capability-degraded behavior before the four-adapter matrix is expanded.

The allocator/store foundation task and the following graph/claims task jointly own this harness. If either exposes a contradiction in the contract, update the spec before building the user-facing skill.

## Quick commands
<!-- scope: technical -->

Focused suites are assigned per task. The final repo gate runs once after propagation:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

Any change to `plugins/flow-next/scripts/flowctl.py` or `flowctl_tracker/` also requires:

```bash
cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl
python3 scripts/gen_tracker_manifest.py
./scripts/sync-codex.sh
./scripts/sync-codex.sh
```

Public docs are verified in a separate clean worktree of `~/work/flow-next.dev`:

```bash
pnpm check
pnpm build
```

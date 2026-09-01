# Running lean - operating profiles

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


flow-next runs fully as **spec -> plan -> work**. Everything else is a layer you can leave off and reach for when a piece of work warrants it. (The plan stage has a recorded direct variant for zero-task specs - the [no-plan route](pipeline-variations.md#no-plan-route); the default framing here is unchanged.)

This page names the two **operating profiles** those layers serve, prices each layer in structural terms, and gives the manual invocation for people who want the capability without the standing cost. It is the source of the optionality caveat that appears at the top of each optional subsystem's page.

> Adjacent, not the same: [`../../../README.md`](https://github.com/gmickel/flow-next/blob/main/README.md) is the happy path, and [`pipeline-variations.md`](pipeline-variations.md) owns the **stage** axis - which stages one piece of work runs, chosen by risk and unknowns (the docs-site page *Menu, Not a Rail* is its doctrine). This page is about which **layers** you switch on at all, and what each one costs you to keep on.

## Two profiles

| | **Human-driven** | **Autonomous** |
|---|---|---|
| Who is watching | You are, at the keyboard | Nobody, until morning |
| What the layers do | Give you a capability on demand | Stand in for the judgment you are not there to apply |
| Default posture | Run lean; add a layer when the work asks for it | Run gated; the gates are what make the run trustworthy |
| Typical shape | `spec -> plan -> work`, plus whatever the change needs | `/flow-next:pilot` + `/flow-next:land` under a host loop |

**Neither is the real mode.** They are two answers to one question: *who applies judgment at each handover?* When you are present, you are the reviewer, the tracker, and the QA - a review backend, a bidirectional tracker sync, and a live QA stage are then buying you convenience, not safety, and you should switch each one on only where the convenience is worth its cost. When nobody is present, those same layers stop being convenience: they are the only thing standing between an unattended loop and an unreviewed merge, and running without them is the actual risk.

The failure mode this page exists to prevent is paying autonomous-profile costs while sitting at the keyboard - a full tracker round-trip on every lifecycle event for a spec only you will ever read.

Profiles are per run, not per team and not per repo. The same repo can drain a backlog autonomously overnight and take a lean human-driven change the next morning.

## The optionality caveat: canonical pattern

**Change this pattern here first.** Each optional subsystem's page carries an instance of it at the top, in this repo and on flow-next.dev. Those instances are deliberate copies (a top-of-page caveat cannot be a link), so edit the shape here and propagate; never fix the shape at an instance.

Three variants, one family:

```text
Optional. flow-next runs fully without this. It costs <structural shape>;
turn it on when <trigger>, or invoke it manually with <command>.

On by default, and droppable. flow-next runs fully without this. It costs
<structural shape>; leave it on when <trigger>, or turn it off and invoke
it manually with <command>.

Deprecated. <what supersedes it>. Nothing is removed yet and existing
setups keep working; <removal route>.
```

Costs are **structural shapes** - "a bidirectional round-trip per lifecycle event", "an extra review pass per task". Never a benchmark number, a timing, or a speed comparison: those age badly, vary by model and repo, and invite the reader to optimize the wrong quantity.

## The layers

Defaults below are read from the published schema ([`../schema/flow-config.schema.json`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/schema/flow-config.schema.json)) - inspect your own with `flowctl config get <key>`.

| Layer | Config key | Default | Lean invocation |
|---|---|---|---|
| [Tracker sync](#tracker-sync) | `tracker.enabled` | off | `/flow-next:tracker-sync` |
| [Live QA stage](#live-qa-stage) | `pipeline.qa` | off | `/flow-next:qa <spec>` |
| [Cross-model review backend](#cross-model-review-backend) | `review.backend` | unset | `/flow-next:impl-review` (draw topology is prose-steered, not a knob) |
| [HTML render lenses](#html-render-lenses) | `artifacts.html.enabled` | off | ask for a render in conversation |
| [Plan-sync](#plan-sync) | `planSync.enabled` | **off** | `/flow-next:sync` |
| [Memory](#memory-and-the-audit-sweep) | `memory.enabled` | **on** | `/flow-next:audit` |
| [Pre-capture discovery](#pre-capture-discovery) | none | manual | `/flow-next:chart`, `/flow-next:prospect` |
| [Autonomous loops](#autonomous-loops) | none | manual | `/flow-next:pilot`, `/flow-next:land` |
| [GitHub scouts](#github-scouts) | `scouts.github` | off | ask a scout in conversation |
| [Ralph](#ralph-deprecated) | none | off, **deprecated** | see below |

### Tracker sync

`tracker.enabled` - **off by default**. Details: [`tracker-sync.md`](tracker-sync.md).

- **Automates away:** keeping a Linear / GitHub / GitLab / Jira issue in step with the spec - body, status, and comments - so people who live in the tracker see current state without anyone retyping it.
- **Costs:** a bidirectional round-trip per lifecycle event you enable it for, plus a conflict policy you now have to hold an opinion about (`tracker.conflictTiebreak`), plus a second place where state can be wrong. Every `tracker.perEvent.*` key you turn on adds another synchronization point to every spec's life.
- **Earns its keep when:** other people - PMs, stakeholders, teammates not in the repo - need to read or edit status where they already work, or when a tracker key is your distributed id allocator for parallel agents (`tracker.specIds`).
- **Lean invocation:** `/flow-next:tracker-sync` on demand. Push a spec to the tracker at the moment you need someone else to see it, and leave the bridge off in between. Spec-only is a first-class mode, not a degraded one: the spec is the source of truth either way.

### Live QA stage

`pipeline.qa` - **off by default** as a pilot stage; the skill is always available. Details: [`../skills/flow-next-qa/SKILL.md`](../../skills/flow-next-qa/SKILL.md).

- **Automates away:** driving the running app like a real user against the spec's acceptance criteria, and filing evidence-backed findings before a human opens the PR.
- **Costs:** a live-app drive pass per spec, a running deploy for the loop to point at, and a driver to be configured and kept working. As a pilot stage it sits between all-tasks-done and make-pr, so every spec pays it.
- **Earns its keep when:** nobody will exercise the app before merge - the autonomous profile's usual case - or when the change is UI/runtime-shaped and tests cannot see the failure mode.
- **Lean invocation:** `/flow-next:qa <spec>` when a change deserves it. If the app is already up on your machine because you just built the feature, you are the live QA pass; the skill is for when you want the findings written down as evidence instead of noticed and forgotten.

### Cross-model review backend

`review.backend` - **unset by default**; reviews run in-host. Details: [`orchestration.md`](orchestration.md#review-backends-cross-model-review).

- **Automates away:** getting a verdict from a model family that did not write the diff, so the reviewer's blind spots are uncorrelated with the writer's.
- **Costs:** an out-of-host review pass per review round - roughly three passes on the first round of each scope, where the codex and host backends fan out three concurrent axis draws and merge them into one fix pass (one round against the cap, not three) - a second CLI installed and authenticated, and a fix-and-re-review loop that can run up to `review.maxIterations` rounds before escalating.
- **Earns its keep when:** the diff was written by an agent and will be merged without a human reading it line by line. That is the autonomous profile by definition; in the human-driven profile you are the cross-model reviewer.
- **Lean invocation:** `/flow-next:impl-review` or `/flow-next:plan-review` on the changes that warrant it, or a per-task `review:` pin, leaving the standing backend unset.

#### Turning the dial: `none` and `host`

The costs above are wall-clock costs in disguise. Each review round is a serial pass the whole pipeline waits on, and the fix-and-re-review loop repeats that wait per round. If you read every diff yourself anyway, the wait buys you little, and the backend has two cheaper settings for exactly that case.

**`none`** switches the review gates off instead of routing them anywhere. Every backend-driven review exits cleanly: the per-task worker review, impl-review, plan-review, and spec-completion-review all skip, and pilot skips its plan-review and completion-review gates rather than deadlocking on them. What still runs is the deterministic spine (Quick commands, full gates, plan-sync) and the in-host quality audit that work dispatches when a change is large or risky. Notice what that leaves out: nothing verifies R-ID coverage at the end of a spec, and a small spec ships on gates alone. Sensible when you are the reviewer; the wrong setting for an unattended loop.

**`host`** keeps every gate alive and runs the reviewer as a host-native fresh-context subagent instead of a second CLI: nothing to install or authenticate, no subprocess. Configuring it takes two lines:

```bash
flowctl config set review.backend host
```

plus a `reviewer:` pin in your `CLAUDE.md` / `AGENTS.md` [routing block](orchestration.md#the-routing-block) naming a model from a family that did not write the diff (ask your harness for current ids rather than copying one from a document). The pin is required because a session model grading its own diff is the blind spot the reviewer exists to remove: without it, interactive runs ask, and autonomous runs stop with `NEEDS_HUMAN` rather than silently self-reviewing.

Between the two: `host` trades the second CLI for zero setup while keeping the gate structure intact; `none` removes the gates themselves. Pick per profile. `none` belongs to the human-driven profile, and an autonomous run should keep at least `host`.

#### Turning the dial: draw topology

On the codex and host backends the first review round of a scope fans out three concurrent axis draws (correctness / contracts / integration) and merges them into one fix pass - a structural trade of parallel review passes for serial fix-and-re-review rounds. The dial is a per-invocation prose instruction, never a flag or config key, and the whole layer is optional to begin with:

- **The default** - three axis draws, one merged fix pass. The right shape when agent-written diffs get merged without a human reading them line by line.
- **Single-reviewer economy** - `/flow-next:work fn-12 - use 1 reviewer instead of 3` collapses the round to one draw: the lean setting for small, clean diffs, where a three-draw harvest costs extra review passes for findings one draw would surface anyway.
- **Cross-family upgrade** - `use three different model families for the review fan-out` routes each draw to a different family, decorrelating blind spots across families as well as axes: the strongest setting for a high-stakes merge.

The worked recipes and the evidence behind the default live in [`orchestration.md`](orchestration.md#steering-the-fan-out-worked-recipes).

### HTML render lenses

`artifacts.html.enabled` - **off by default**. Details: [`html-artifacts.md`](html-artifacts.md).

- **Automates away:** rendering a spec or a PR as a self-contained HTML page for people who will not read markdown in a terminal.
- **Costs:** an extra render step on capture, plan, and make-pr, and an artifact tree to decide whether to commit or ignore.
- **Earns its keep when:** you are handing a spec to a business reviewer, or a PR to someone reviewing decisions rather than diffs.
- **Lean invocation:** ask for the render in conversation when you need one. Markdown stays the source of truth in every case, so a lens is always regenerable and never has to exist in advance.

### Plan-sync

`planSync.enabled` - **off by default since 4.5.1** (earlier inits wrote `true`; an existing config keeps its value). Details: [`../skills/flow-next-sync/SKILL.md`](../../skills/flow-next-sync/SKILL.md).

- **Automates away:** updating downstream task specs after an implementation drifts from what the plan assumed, so later tasks re-anchor on what is true rather than what was planned.
- **Costs:** a reconciliation pass after each completed task - which usually finds nothing to change, which is why it now ships off.
- **Earns its keep when:** the spec has several dependent tasks and implementations genuinely drift from the plan. Opt in with `flowctl config set planSync.enabled true`.
- **Lean invocation:** leave it off and run `/flow-next:sync` when a task genuinely invalidates a downstream assumption - manual sync keeps the full capability.

### Memory and the audit sweep

`memory.enabled` - **on by default**. Details: [`memory-schema.md`](memory-schema.md).

- **Automates away:** carrying learnings across context compaction and across sessions, so a bug class you already diagnosed does not get re-diagnosed from scratch.
- **Costs:** the memory tree itself is nearly free - entries are written as a side effect of work already happening and read by search, not loaded wholesale. The **audit sweep** is the layer with a price: a pass over every entry to judge it against the current codebase.
- **Earns its keep when:** memory is on, always. The audit earns its keep once entries have had time to go stale - after a refactor that invalidates prior art, or on a periodic cadence.
- **Lean invocation:** leave memory on; run `/flow-next:audit` deliberately rather than on a schedule.

### Pre-capture discovery

No config key - these are skills you invoke or do not. Details: [`../skills/flow-next-chart/SKILL.md`](../../skills/flow-next-chart/SKILL.md), [`../skills/flow-next-prospect/SKILL.md`](../../skills/flow-next-prospect/SKILL.md), [`../skills/flow-next-interview/SKILL.md`](../../skills/flow-next-interview/SKILL.md).

- **Automates away:** finding out what to build - a ranked backlog (`prospect`), a decision map for one oversized unclear idea (`chart`), or structured requirement extraction on an existing spec (`interview`).
- **Costs:** a discovery loop before any code exists. Chart in particular is an adaptive multi-invocation loop, one decision per tick.
- **Earns its keep when:** you cannot yet state the outcome in a sentence. When you can, capture directly; discovery on an idea you already understand is ceremony.
- **Lean invocation:** all three are already manual and none is ever a required stage. `/flow-next:guide` will tell you which, if any, your situation needs.

### Autonomous loops

No config key to enable; `pilot.autonomy` (`ready` by default) only widens what pilot selects. Details: [`../skills/flow-next-pilot/SKILL.md`](../../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../../skills/flow-next-land/SKILL.md).

- **Automates away:** the repetition - pilot advances one ready spec by one stage per tick, land babysits the resulting PRs to merged.
- **Costs:** this is the autonomous profile itself, so it inherits the profile's gates: the layers above stop being optional in the way they are optional for you at a keyboard, because they are what replace you.
- **Earns its keep when:** there is a queue of blessed, fully specified work and nobody who wants to sit through it.
- **Lean invocation:** `/flow-next:work` is the human-driven equivalent and needs no loop primitive at all.

### GitHub scouts

`scouts.github` - **off by default**.

- **Automates away:** pulling implementation patterns out of public and private GitHub repos during planning.
- **Costs:** an extra scout dispatch on planning fan-outs, and network reach into repos during a stage that otherwise reads only your checkout.
- **Earns its keep when:** you are adopting an unfamiliar library or protocol and want prior art rather than first principles.
- **Lean invocation:** ask for the search in conversation when a plan actually needs it.

### Ralph (deprecated)

**Deprecated.** A shell script that calls the orchestration primitives - `/flow-next:pilot` to build and `/flow-next:land` to ship, driven by a host loop or `cron` - does what the hardened harness does, without the `scripts/ralph/` scaffold, the guard-hook registration, and the second receipt plumbing. Nothing is removed yet and existing Ralph installs keep working unchanged; new adopters should reach for pilot + land. Details and the full comparison: [`ralph.md`](ralph.md).

### Implementation offload (no layer to enable)

Offloading implementation to a second CLI is **not an optional layer** - there is no config key to switch on and nothing to price. You drive the other CLI through a headless bridge, ad hoc or as standing routing prose in `CLAUDE.md` / `AGENTS.md` (written for you by the `/flow-next:setup` model-routing scaffold). The recipes, the tier advice, and the rule that the bridged child writes code while the host keeps git, judgment, and the verdict live in the usage guide's `## Orchestration & model steering` section. Details: [`orchestration.md`](orchestration.md#implementation-offload-the-bridge-route).

## A lean run still leaves a record

Running lean does not mean running unaccountably. Every orchestrated stage records its outcome as `ran`, `skipped(reason)`, or `failed(reason)` in the receipts it already writes, so a stage you deliberately left off is an explicit entry with your reason attached rather than a silent absence:

```bash
flowctl usage --stages <spec-id>        # plain
flowctl usage --stages <spec-id> --json # machine-readable
```

That is what makes a deliberate layer set auditable later: the difference between "QA was off because this is a CLI change with no live surface" and "QA never ran and nobody knows why" is visible in the receipt, not reconstructed from memory.

## See also

- [`../../../README.md`](https://github.com/gmickel/flow-next/blob/main/README.md) - the happy path and the 5-command quick start.
- [`pipeline-variations.md`](pipeline-variations.md) - the stage axis: six worked routes through the menu, selected by risk and unknowns.
- [`orchestration.md`](orchestration.md) - which model does what, and how to change it. The routing counterpart to this page: same doctrine, applied to models rather than layers.
- [`../skills/flow-next-guide/SKILL.md`](../../skills/flow-next-guide/SKILL.md) - `/flow-next:guide`, the router that recommends the smallest sufficient workflow for one specific situation.
- [`teams.md`](teams.md) - what changes when several humans and several agents share one repo.
- [`architecture.md`](architecture.md) - what `.flow/` holds regardless of which layers you run.

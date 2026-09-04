# Orchestration & model routing

flow-next is an orchestration layer, not a single-agent workflow. The host agent (Claude Code / Codex / Droid) conducts: it fans work out to tiered subagents, routes reviews to a *different* model family than the writer, optionally drives a second CLI agent through a headless bridge, and runs autonomous build/ship loops. Which model does what is a routing decision - and every routing decision in flow-next is either a parameter or a sentence of intent away. The second kind carries judgment.

The pattern this page serves: use your smartest model to orchestrate and judge, route mechanical or token-hungry work to faster/cheaper models, and pick reviewers from a different family than the writer. flow-next was built in this shape - this page maps the dials.

**None of this is required.** The skills and subagents ship pre-tuned to work well out of the box for everyone - review defaults sensible, the pipeline complete with zero routing config. Steering is a capability, not a prerequisite: reach for the dials below when your model mix, subscriptions, or taste differ from the defaults, and ignore this page entirely until they do. The same doctrine applied to subsystems rather than models - which layers to switch on at all, and what each costs - is [`running-lean.md`](running-lean.md).

## Contents

- [Tiers: what kind of model a job wants](#tiers-what-kind-of-model-a-job-wants)
- [Reach: how this harness gets one](#reach-how-this-harness-gets-one)
- [Two ways to route](#two-ways-to-route)
- [Deterministic routing: the parameter surfaces](#deterministic-routing-the-parameter-surfaces)
- [Prompted orchestration: routing with judgment](#prompted-orchestration-routing-with-judgment)
- [Field patterns, mapped to flow-next](#field-patterns-mapped-to-flow-next)
- [A default pipeline, expressed as tiers](#a-default-pipeline-expressed-as-tiers)
- [Durable routing: the routing block in your instruction file](#durable-routing-the-routing-block-in-your-instruction-file)
- [Chaining the loops](#chaining-the-loops)
- [Unattended chart driving (not a pilot stage)](#unattended-chart-driving-not-a-pilot-stage)
- [In your repo](#in-your-repo)
- [What stays fixed](#what-stays-fixed)
- [See also](#see-also)

## Tiers: what kind of model a job wants

Two words carry the whole routing story. A **tier** is what kind of model a job wants. **Reach** is how the active harness obtains one - the in-session model, an in-host subagent, shelling out to another CLI, or not available.

**This section is the single definition of the tier names.** They are a user-facing interface, chosen once; anywhere else in flow-next that routes work refers back here rather than restating them.

| Tier | What it means |
|---|---|
| **reviewer** | Anything grading work someone else produced. The only tier carrying a family rule: a reviewer from the writer's own family is not an independent verdict. |
| **implementer** | Work handed to another harness. The load-bearing case - plan on the session model, implement somewhere cheaper or faster. Absent, the session model implements. |
| **fast scout** | Mechanical inventory scanning, where the cheapest model is the correct one. |
| **thinking scout** | Analysis that degrades badly on a fast model. |
| **unset** | The default, and the majority: planning, capture, interviews, requirement analysis, every verdict, and the worker run on the session model. This is the never-delegate-judgment doctrine, stated as the default rather than as a special case. |

A fifth name would be a breaking change to a user-facing interface. An **unrecognized tier name is treated as unset**, with one advisory line - never an error.

**A tier says which model executes a stage, not which stages run.** Which stages run is decided by what you invoked; asking for a leaner pipeline is a separate instruction that already works.

**The family rule is advice, not enforcement.** A model's family cannot be verified from a name you invented, so the reviewer tier documents the rule, the receipt records what ran, and nothing fails closed on it.

### The routing block

Preferences live in **your** instruction file (`CLAUDE.md` / `AGENTS.md`), in your own words, naming models you can verify against your own account. One line per tier:

```markdown
reviewer: <model>
implementer: <model> at <effort>
fast scout: <model>
thinking scout: <model>
```

An absent tier means the session model. An unparseable line is ignored with one advisory, never an error. Effort semantics stay the host's - flow-next passes effort through and never translates between vendors' scales. `/flow-next:setup` proposes this block commented out, for you to edit; nothing infers availability into it, and nothing rewrites a block a human has edited.

The block is the durable form of an ad-hoc instruction. Written once, it is read every turn - and an explicit instruction in the moment still wins over it, which is exactly the precedence below.

Worked example, in a consumer's own words:

```text
you conduct + review (frontier, medium effort); implementation goes to
<another model> via <its CLI>, one task per dispatch
```

### Routing precedence

**Routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.**

There is no error surface: the chain terminates at the session model by construction. Agent definitions keep their model field as the **floor** - what applies when nothing overrides - which is why a repo with no routing block behaves exactly as it always has. The review backend is separate: it keeps its own `backend[:model[:effort]]` configuration and its own documented precedence ([Review backends](#review-backends--cross-model-review)).

A model this harness cannot reach - another vendor's identifier, a retired one, one your account lacks - falls back to the session model, says so once, and continues. No probing, no question, no failure.

## Reach: how this harness gets one

Reach is documented **once per harness**, never inside a skill: a skill asks for a tier, and never names a spawn primitive, a CLI flag, or a vendor path. Each page states which mechanisms exist there, which do not, the degradation when one is missing, and how to discover what the harness offers instead of trusting a stored answer.

[`reach/README.md`](reach/README.md) - index and the four questions every page answers · [Claude Code](reach/claude-code.md) · [Codex](reach/codex.md) · [Droid](reach/droid.md) · [Cursor](reach/cursor.md) · [Grok Build](reach/grok-build.md) · [OpenCode](reach/opencode.md) · [generic fallback](reach/generic.md)

An undetectable harness resolves to the generic page and says so. **Discovery beats declaration:** where a harness can list what it offers, ask it - one command beats a stored fact that goes stale.

## Two ways to route

**Skills are prompts executed by the host agent, not compiled code.** That gives you two genuinely different routing methodologies - use both:

| | **Deterministic - parameters** | **Prompted - agentic intelligence** |
|---|---|---|
| What it is | Config keys, flags, env vars, per-spec/per-task fields. Machine-resolved, same answer every time | Policy described in natural language. The host *judges* per item - conditionally, mid-run, against context no parameter can see |
| Example | `flowctl config set review.backend codex` | "Work the three ready specs - decide per spec, by complexity, whether implementation goes out to a codex bridge or stays on the session model" |
| Reach | Exactly the surfaces that ship (below) | Anything the host can do - including capabilities that don't exist as parameters |
| When it wins | Headless/Ralph runs, stable team defaults, reproducibility | Per-item complexity calls, conditional escalation, one-off arrangements, inventing a routing the registry doesn't have |

The two compose: parameters set the floor, prompting steers above it. And either can be made durable by writing it into `CLAUDE.md` / `AGENTS.md` - the host reads your instruction files every session, and flow-next skills inherit them automatically because the host is the one executing them.

### Two layers of steering: session vs machinery

The table above is really two layers with a clean seam, and knowing which layer you are talking to answers most "will this override that?" questions:

- **Session steering** - your prompts and per-task pins. Top of the precedence chain, ephemeral, done the moment the task is done. Naming a model for a tier in the moment - *"implement via that CLI and review with the other family"* - just works: the agent runs the bridge for the draft and pins the named reviewer, and **nothing persists afterward** - pins and defaults resume untouched. Your `CLAUDE.md` routing prose lives in this layer too: deterministic plumbing never reads prose, but the *agent* reads it every turn and feeds explicit values downward, so a `CLAUDE.md` pipeline dominates everything the agent orchestrates by occupying the higher-precedence rung - not by editing config.
- **Machinery steering** - config resolved by deterministic plumbing that never reads prose: `review.backend` and the per-spec/per-task backend fields. This is what autonomous loops (pilot, Ralph, land ticks) and unattended gates use when nobody is prompting. Standing changes for autonomous runs belong here, not in prose.

For the models that execute stages, the chain is the one stated above: **routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.** The review backend resolves separately, through its own configuration grammar - see [Review backends](#review-backends--cross-model-review) for that chain; the tiers above never touch it. One consequence worth spelling out: a prompt can steer only the session it is typed in - if you want pilot ticks at 3am to use a different reviewer, that is a config change (`flowctl config set review.backend ...`), because at 3am there is no prompt.

## Deterministic routing: the parameter surfaces

### The host model: the conductor

You pick it in your harness (e.g. `/model`). The host owns everything that requires judgment: gating, task classification, git, review-verdict interpretation, user consent. Workers and resolvers ship with `model: inherit`, so the session model *is* the implementation model unless you route implementation out over a bridge (below). Practical consequence: a frontier session model gives you a frontier planner *and* frontier workers; dropping the session model for a mechanical spec drops both.

### Agent defaults: the floor

Bundled agents carry a model field grouped by task shape - the family alias in each agent's own frontmatter is the source of truth (`agents/*.md`). These are **defaults**, not pins: they are the third rung of the routing precedence, so an explicit argument or your routing block overrides them, and a repo with neither behaves exactly as shipped.

| Agent group | Agents | Why |
|------|--------|-----|
| fast | prime's pillar scanners (build/env/security/testing/tooling/workflow/observability) + memory-scout | mechanical scan-and-report |
| judgment | planning scouts (repo/context/spec/docs/github/practice, …), flow-gap-analyst, plan-sync | read-and-judge, bounded scope |
| heavy | quality-auditor | adversarial audit |
| `inherit` | worker, pr-comment-resolver | implementation follows the session model |

The Codex mirror maps these groups to that host's own tiers at sync time (`scripts/sync-codex.sh` `map_model`); the sync-time environment overrides them. The worker keeps `inherit` on both platforms (your session model rules); an OPT-IN sync-time pin lets Codex-host work threads ride a cheaper tier. Details: [`platforms.md`](platforms.md).

**Cursor host:** canonical `agents/*.md` family aliases resolve to **inherit** (the session model) when running on a Cursor host. Caller-side model pins in the dispatch itself are the escape hatch for picking a specific model. There is no alias-to-slug rewrite mechanism and none is planned.

**Per-host reach - including which hosts cannot honor an agent's model field, and what the degradation is - lives in [`reach/`](reach/README.md), one page per harness.**

### Review backends: cross-model review

> **Optional.** flow-next runs fully without this; `review.backend` is unset by default and reviews run in-host. It costs an out-of-host review pass per review round, a second CLI installed and authenticated, and a fix-and-re-review loop that can run up to `review.maxIterations` rounds; turn it on when agent-written diffs get merged without a human reading them line by line, or invoke it manually with `/flow-next:impl-review` on the changes that warrant it. Two cheaper standing settings exist: `none` switches the review gates off entirely (each review skill exits cleanly, and pilot skips its plan-review and completion-review gates), while `host` keeps every gate and runs the reviewer as a host-native fresh-context subagent with a cross-family `reviewer:` pin from [the routing block](#the-routing-block) - no second CLI. The trade is priced in [`running-lean.md`](running-lean.md#turning-the-dial-none-and-host).

The review subsystem is the most routable surface. Spec grammar `backend[:model[:effort]]`, registry `rp | codex | copilot | cursor | host | none` (`host` is bare-only - no model/effort rungs). The three CLI review backends (`codex` / `copilot` / `cursor`) are `BACKEND_REGISTRY` entries driving one shared `cmd_backend_review` pipeline (fn-112); genuine variance is hooks, not cloned commands.

```bash
flowctl config set review.backend codex                    # project default
flowctl config set review.backend cursor:<model>          # cursor folds effort into the model name
flowctl config set review.backend codex:<model>:xhigh     # explicit model + effort
flowctl config set review.maxIterations 6                 # review-round cap (env MAX_REVIEW_ITERATIONS wins; >= 1, human-only under Ralph)
```

Precedence (highest wins): per-task `review:` / per-spec `default_review` → `FLOW_REVIEW_BACKEND` → `.flow/config.json` `review.backend` → backend-specific env → registry default. A single task can pin a different reviewer than the project default and the override routes end-to-end. The `cursor` backend reaches reviewer models from several families in one place, on your existing Cursor subscription - ask its CLI for the current list rather than copying identifiers from a document. Full grammar + registry: [`flowctl.md`](flowctl.md#review-backend).

**The review prompt carries identities, not payloads (fn-169).** A reviewer runs
in your checkout with a shell, so it is an executor like any other agent: flow-next
hands it the rubric, a `<base-sha>..<head-sha>` range, `git diff --numstat --no-renames`
as the exact scope map, and repo-relative spec/task paths - then the reviewer fetches
what it needs at whatever depth each hunk warrants. It does **not** ship the diff
body, the spec text, or the task specs. That is not a size optimisation with a
quality cost; the payload was the quality cost. The diff body used to be capped at
50 KB, so on a 495 KB change the reviewer received ~10% of the evidence its verdict
rested on and fetched the rest anyway. `--numstat --no-renames` matters more than it
looks: plain `--stat` abbreviates paths (`.../pr-cognitive-aid/.write.lock`) and
plain `--numstat` collapses renames into `{old => new}`, and a scope map you cannot
resolve to paths is not a scope map.

Two consequences are load-bearing rather than incidental. First, **a prompt-payload
fitter or truncator is evidence the payload is wrong** - flow-next kept exactly one
size guard, `CURSOR_ARGV_TRANSPORT_MAX`, and it is named as *transport* because
`cursor-agent` takes its prompt as a positional argv argument and Windows
`CreateProcessW` has a hard limit. It refuses loudly; it never trims. Second, an
evidence read that FAILS aborts before a review round is reserved, because with
nothing embedded an empty scope map is not a degraded review, it is no review.

**Prior findings ride the session, not the prompt (fn-169).** Re-reviews resume the
reviewer's own session, so it already holds the findings it made - the round sends
the shrink-only contract and the reply grammar, and re-renders nothing. Injection is
the fallback: if the resume fails, flow-next rebuilds the prompt *with* the findings
and dispatches fresh. The order is deliberate - a lean prompt reaching a
context-free session would be a fresh blind review with the priors dropped, which is
the runaway this machinery exists to stop. Two-phase resume is enabled for `codex`,
whose resume is measured; `copilot` (whose `--resume` is create-or-resume via a
marker) and `cursor` inject unconditionally. `host` always injects - it has no
session by design, every re-review being a fresh subagent. Injecting when it was
unnecessary costs bytes; not injecting after a silent resume failure costs a blind
review, so injection is the default everywhere it is not provably unnecessary.

**The first review round fans out three axis draws (fn-215).** On the `codex` and
`host` backends, the first round of a review scope is three draws of the
same reviewer - same resolved backend/model, same base prompt, each differing by
exactly one added axis line - dispatched concurrently where the host offers
one-message parallel dispatch, back-to-back with the degradation disclosed in the
review record otherwise: correctness-and-logic of the changed code,
contracts-and-consistency (do docs, tests, and stated promises agree with what the
code does), and integration-with-unchanged-code. The studies behind this measured
single-pass review recall as stochastic sampling - roughly 45% of validated
findings per draw, with a union of three axis-differentiated draws recovering
1.56x single-draw recall (against a pre-registered 1.5x bar) at flat validity - so
one merged round harvests most of
what previously trickled out across many serial rounds. The coordinator merges the
draws (same-defect dedupe, evidence-bar drops with a count, ranked output with an
Act-On tier capped at 5 non-blocking plus a published remainder) and runs ONE
consolidated fix pass; the merged round consumes ONE review round against the cap,
not three. Re-review rounds after fixes are a single dispatch carrying the full
merged prior-finding container - the harvest value is the first round, and
re-review verifies fixes, which needs continuity, not breadth. `rp` keeps its
single stateful chat, and `copilot` / `cursor` keep single dispatch every round.
The residual is real: roughly a third of validated findings eluded every draw in
the studies, so round 2 shrinks rather than disappears.

**Rule of thumb: the model that writes is never the model that reviews.** Route the reviewer to a different family than your session model and blind spots stop being correlated.

**Ambient-instruction contamination + persona override (fn-90, extended to codex by fn-187 / #331).** A reviewer subprocess can inherit instructions that were never meant for it, and each backend has its own channel:

- **cursor** - `cursor-agent` has **no system-prompt mechanism**: the flow-next reviewer rubric travels as a plain user prompt *on top of* Cursor's own built-in persona (which carries its OWN review rubric and an end-to-end-thoroughness bias), and `cursor-agent` auto-attaches the workspace `AGENTS.md` / `CLAUDE.md`, skill catalogs, and MCP instruction blocks. That ambient guidance dilutes the in-scope anchor and biases the reviewer toward always-produce-findings - an amplifier of review-loop non-convergence, not the root cause. There is no cursor CLI knob to suppress the auto-attach.
- **codex** - `codex exec` auto-loads the host repo's project doc (`AGENTS.md`); in a repo whose `AGENTS.md` routes all work through the flow-next skills, the reviewer adopts that role and re-dispatches the review at itself instead of performing it (#331 route A - suppressed at the argv level with `-c project_doc_max_bytes=0` on both the fresh and resume dispatch). With the flow-next codex plugin installed, the reviewer can also read the plugin's own coordinator skills ("never self-declares a verdict") and obediently withhold the verdict tag (#331 route B - no CLI knob exists).

On both backends flow-next prepends an explicit **persona-override preamble** on every review path: it declares that any ambient rubric/persona/instruction from the environment - built-in persona, auto-attached `AGENTS.md`/`CLAUDE.md`, skill catalogs, MCP blocks - is *superseded*, and the ONLY rubric + verdict contract is the flow-next one that follows. Repo-specific review invariants belong in `.flow/criteria.md` (standing G-IDs), which rides the review prompts themselves and reaches every reviewer regardless of backend - `AGENTS.md` is host-agent operating instructions, not a review-criteria channel, and a reviewer that inherits it returns no verdict at all rather than a stricter one (#331). Documented, not configurable; it rides automatically on `review.backend cursor:*` and `codex`. A review that still completes with no verdict is journaled as `missing_verdict` (not a transport failure class), and a streak of those terminates with instruction-contamination guidance instead of "repair the backend". The structured-findings ratchet and deterministic convergence terminals (unchanged-artifact refusal, early escalation when the reviewer explicitly marks the same finding `not-fixed` in two consecutive rounds, the round cap, and reviewer-emitted `NEEDS_HUMAN`) apply to every backend - see [`flowctl.md`](flowctl.md#codex-impl-review).

#### Steering the fan-out: worked recipes

Reviews are optional to begin with - the fan-out is a property of a layer you
already opted into - and its topology is steered by prose, never by a flag or a
config key. Three phrasings cover the dial:

- **The default** - say nothing. Three axis draws on the resolved backend, merged
  into one fix pass: the evidence-favored shape when agent-written diffs get
  merged without a human reading them line by line.
- **Single-reviewer economy** - `/flow-next:work fn-12 - use 1 reviewer instead of 3`
  (the same phrasing works on `/flow-next:impl-review`). The round collapses to a
  single draw - the right call on small, clean diffs, where the three-draw harvest
  pays roughly 3x review tokens for findings one draw would surface anyway.
- **Cross-family upgrade** - `use three different model families for the review
  fan-out`. The three draws route to explicitly named per-draw backends/models,
  one per family, so blind spots decorrelate across families as well as axes -
  the strongest shape for a high-stakes merge. One structural constraint on the
  codex backend: the primary draw - correctness, or the first draw when
  correctness is not drawn - stays on codex (round 2+ resumes its session, and
  the merged receipt's top-level fields come from it); secondary draws may name
  `codex`, `copilot`, or `cursor`. On the host backend the per-draw model pins
  are unconstrained.

All three resolve through the existing routing precedence - an explicit
instruction in the moment wins - and the coordinator owns the parse: it turns the
phrasing into explicit per-draw specs passed to the fan-out interface as
arguments. flowctl never reads prose.

### Implementation offload: the bridge route

Offloading the token-heavy part (writing code) to a second CLI is a **routing decision you write, not a subsystem you configure**. There is no packaged delegation mode and no `work.delegate*` config: you drive the other CLI through a headless bridge, either ad hoc in the session or as standing policy in `CLAUDE.md` / `AGENTS.md`.

```bash
codex exec -m <model> -c model_reasoning_effort=<effort> "<self-contained prompt>"
cursor-agent --model <model> --force "<self-contained prompt>"
claude -p "<self-contained prompt>"     # the same bridge in reverse, from a Codex/Cursor host
```

Two rules survive from the packaged path and are not optional:

- **The bridged child writes code; the host keeps git, judgment, and the verdict.** The child never commits, never decides scope, never issues a review verdict, and never spawns a bridge of its own. Drop this and a bridge recipe becomes an unbounded second agent.
- **Which tier to bridge to:** on well-specified work a value-tier implementer matches a strong-tier one on correctness at roughly two-thirds the wall clock, so send clear, well-scoped tasks to the value tier and escalate to the strong tier only for genuinely gnarly ones. Spec quality is what makes the trade safe - a vague brief burns the saving on rework.

Full recipes (including the thin-wrapper pattern for unattended loops): the usage guide's `## Orchestration & model steering` section - `flowctl usage`. Make it durable by writing the routing into your instruction file: [Durable routing](#durable-routing--a-model-table-in-claudemd).

### Per-spec backend fields: external orchestrators

The data model carries routing even where flow-next itself doesn't consume it: `flowctl spec set-backend fn-1 --impl codex:<model> --review claude:<model> --sync claude:<model>` sets per-spec impl/review/sync backend specs for orchestration products built on top of flow-next (e.g. control planes that dispatch one CLI per spec). See [`flowctl.md`](flowctl.md#spec-set-backend).

## Prompted orchestration: routing with judgment

This is the mode parameters can't reach: the host is an intelligent orchestrator, so routing policy can be *conditional* and *per-item*, decided against the actual work rather than fixed up front.

**Per-item complexity routing** - the host classifies, then routes:

```text
Work through the three ready specs. Decide per spec, based on complexity,
how the work stage runs: anything touching auth or the migration you
implement yourself on the session model; plain CRUD goes out to a codex exec
bridge. Reviews come from codex either way.
```

**Focus and scope steering** - instruction the skill never anticipated, read as intent:

```text
/flow-next:plan fn-12 --depth=deep — focus the research on the migration path; I care about rollback
/flow-next:interview fn-12 — push hard on failure modes and operational edges, skip UI polish
/flow-next:work fn-12 — the UI tasks stay with you; send the API plumbing out to a codex bridge
```

**Conditional escalation** - routing that reacts to outcomes:

```text
Run /flow-next:work fn-12 and bridge implementation to codex exec. If a task's
review comes back NEEDS_WORK twice, stop bridging that task and implement it
yourself on the session model.
```

**Prompting a capability into existence** - no registry entry exists for a session-model reviewer; that didn't stop this repo's own loop from running fresh-context, session-model-reviewed rounds:

```text
/flow-next:plan-review fn-12 — don't use the configured backend; spawn a
fresh-context subagent on the session model with the same review criteria,
and feed its verdict into the fix loop like any other reviewer.
```

Backends, reviewers, and bridged implementers are prompts plus plumbing - when a rung you want is missing, describe it and the host builds the arrangement on the spot. The deterministic flags (`--review=<backend>`, `--depth=short`) still work inline for the parts that *are* parameterized; prompting composes around them.

## Field patterns, mapped to flow-next

The orchestration patterns that emerged in the wild through mid-2026 all have a direct flow-next expression - most need one config key or one sentence:

| Pattern from the field | The idea | flow-next expression |
|------------------------|----------|----------------------|
| **Orchestrator → executor** | The frontier model plans and judges; a cheaper, highly steerable model (the implementer tier, on a subscription you already pay for) writes the code | A `codex exec` bridge recipe, ad hoc or as standing prose in `CLAUDE.md`. Host keeps gating/git/review; the bridged child writes code |
| **Orchestrator → reader** | Token-hungry, low-judgment reads (codebase analysis, doc sweeps) run on fast models that report summaries back - the orchestrator never holds the raw tokens | Already the default: planning scouts and prime scanners run on the fast tiers and return digests. Add `/flow-next:map` for token-efficient exploration |
| **Cross-family reviewer** | The model that writes is never the model that reviews - uncorrelated blind spots | `review.backend <backend>` - per-task `review:` pins exceptions |
| **Effort discipline** | Run the orchestrator at high, not max - top effort tiers are token furnaces with flat-or-worse output on routine work | Session effort is yours; a bridged child takes its effort inline (`-c model_reasoning_effort=medium` is the recommended floor - raise it for gnarly tasks) |
| **Token-hungry offload** | Computer use, live-app verification, bulk analysis go to other models/agents; results come back as evidence | `/flow-next:qa` drives the app in its own context and files P0/P1/P2 findings; workers run fresh-context and return receipts |

## A default pipeline, expressed as tiers

The routing this repo runs, stated in [tier](#tiers--what-kind-of-model-a-job-wants) terms. It names no model identifiers on purpose: which model fills a tier is a property of your account and your harness, and only you can name it.

| Stage | Tier | Why |
|---|---|---|
| Plan (capture / interview / plan / plan-review critique) | unset - the session model | Spec authoring is inline and judgment-heavy; this is the never-delegate-judgment default |
| Plan-review | reviewer, from a different family than the planner | Uncorrelated blind spots on the highest-leverage artifact |
| Work (implementation) | implementer | Well-specified work runs correctly on a cheaper or faster tier; the saving is real only when the spec is clear |
| Impl-review, first pass | reviewer, measured from the **writer** - not the host | A reviewer from the family that wrote the diff re-correlates the blind spots |
| Impl-review, final gate | unset - the session model | The verdict, the severity call, and the blast-radius judgment stay with the conductor |

Notes that keep this honest:

- **Single subscription? It still reads correctly.** Every tier degrades to the session model, and the pipeline works exactly as shipped - routing is optional garnish, never a prerequisite.
- **Reach differs per harness, the tiers do not.** The bridges run in both directions, so the same tier assignment holds everywhere; only how you get there changes. See [`reach/`](reach/README.md).
- **The family rule is advice, not enforcement.** Nothing can verify a model's family from a name you invented; the reviewer tier documents the rule and the receipt records what ran.
- **Scouting splits by kind of work, not by price.** Mechanical inventory goes to the fast scout tier; analysis that degrades on a fast tier goes to the thinking scout tier.

**Work-stage scheduling:** `/flow-next:work` schedules on the rolling frontier by default - a new ready task is admitted at every worker-return event, with isolated per-task workspaces and conductor-owned review - and falls back to the wave loop for a task-id run, when plan-sync is on, when the spec has fewer than two open tasks, or when its tasks form a sequential chain. The route prints once as `Scheduling: rolling | wave (<reason>)`; pilot and land dispatch plain `/flow-next:work` and inherit it. Details: [`../skills/flow-next-work/references/rolling-scheduler.md`](../skills/flow-next-work/references/rolling-scheduler.md).

### The wrapper pattern: self-healing bridges for unattended loops

Raw bridge calls have a silent-failure class: outside a trusted git directory, `codex exec` refuses in about a second with the error only in its log, and `cursor-agent` blocks on an interactive workspace-trust prompt, then exits "successfully" with empty output. An interactive host sees the stderr and just fixes it; an **autonomous loop dies silently**. The pattern that closed this in the eval: wrap the bridge in a thin fast-tier subagent instead of calling it raw. The wrapper composes the self-contained prompt, runs the bridge, verifies output is non-empty/parseable, repairs the environment if not, and retries once. Output quality was identical to raw calls.

Two rules are load-bearing:

- **The wrapper MUST run the bridge in the foreground** - one blocking Bash call. A backgrounded bridge loses the completion signal and the wrapper idles forever on a finished (or silently dead) process.
- **The self-heal license covers environment and flags only, never judgment.** In scope: git trust (`--skip-git-repo-check`, `git init` in a scratch dir), sandbox flags, stale model ids, empty-output retry. Out of scope: rewriting the task prompt, interpreting review verdicts, or switching models on quality grounds - judgment stays with the host.

This is a documented pattern, not a shipped agent type - the bridge recipes live in the usage guide's `## Orchestration & model steering` section (`flowctl usage`). Interactive sessions don't need it.

### Raw-bridge review prompts: demand severity tiers

Applies to **ad-hoc bridge reviews only** - a hand-rolled `codex exec` review whose output a human reads directly (the usage.md recipes). When you write one, put two things in the prompt:

- **P0-P3 severity tiers plus spec-grounded verdicts**, so an edge-case finding does not flip a ship gate. Reviewers reliably flag spec-gray edges as bugs (in the eval, behavior explicitly licensed by a plan amendment was reported as a defect by every reviewer) - severity tiers and "cite the spec line" are what keep those findings informative instead of gate-flipping.
- Optionally **a minimal suggested fix and blast radius per finding** when no fix loop follows the review. Control runs showed this artifact is prompt-shaped: models produce it when the prompt demands it and omit it when not asked.

The **packaged** `/flow-next:impl-review` prompt is deliberately NOT changed to this shape: its find-vs-fix split (the reviewer returns findings; the internal fix loop investigates and fixes, with validator and iteration caps) is by design, and its rubric already carries confidence anchors and introduced-vs-pre-existing classification. Deep-pass/validator merge math is autonomous-only (fn-113.4): under `FLOW_RALPH` / `REVIEW_RECEIPT_PATH` / `FLOW_AUTONOMOUS` flowctl mutates the receipt; interactive surfaces raw findings and the host judges.

## Durable routing: the routing block in your instruction file

Session steering is a sentence you type; **durable** steering is the same sentence written once into `CLAUDE.md` / `AGENTS.md`, where the host reads it every turn. That is the routing block: `<tier>: <model>` lines, optionally `at <effort>`, interpreted by intelligence rather than parsed by a config loader - which is why it can be prose and why an unreachable name degrades instead of failing.

`/flow-next:setup` offers to scaffold it from [`../skills/flow-next-setup/templates/model-routing-snippet.md`](../skills/flow-next-setup/templates/model-routing-snippet.md): the four tier lines with their guidance, **every value commented out**, so nothing routes until you fill one in. Setup never asserts which models are installed and never overwrites a block a human has edited. Marker-fenced, so `/flow-next:uninstall` removes it cleanly.

The grammar and the tier meanings are [above](#the-routing-block); the block is yours to edit afterwards. Tier names are durable; model identifiers are volatile - that asymmetry is the whole reason routing is expressed as tiers here and as model names only in your file.

## Chaining the loops

Pilot and land end every tick with machine-readable verdict lines precisely so a host driver can compose them. Pilot never merges and never invokes land (consent boundary); the *driver* routes between them:

```text
/loop 30m — one tick: run /flow-next:pilot --review=codex.
  If it prints PILOT_VERDICT=DEFERRED_TO_LAND, run /flow-next:land in the same tick.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK, or on any NEEDS_HUMAN.
```

`DEFERRED_TO_LAND` exists exactly for this hand-off - every remaining spec has an open PR that land, not pilot, owns. Compose model routing into the same driver and you have a multi-model spec-to-merged-PR pipeline in one prompt:

```text
/loop 30m — one tick: run /flow-next:pilot --review=codex --depth=deep.
  If PILOT_VERDICT=DEFERRED_TO_LAND, run /flow-next:land in the same tick.
  Send implementation tasks to the implementer tier,
  keep UI tasks on the session model, reviews come from codex.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK,
  or on any NEEDS_HUMAN.
```

### Within one pilot invocation vs across driver invocations

The driver composition above composes pilot *into* land inside one driver tick; successive pilot stages still land on successive driver invocations - by default every pilot invocation advances one stage, and the loop interval is the seam between stages. `pipeline.chainStages` (`off` by default) chains *within one pilot invocation*, for the one transition whose outcome is already decided when the stage ends: a `qa` stage that verified a fresh terminal `qa_outcome` runs `make-pr` in the same tick, so the driver no longer pays an interval plus a full re-anchor to open a draft PR it was always going to open. The table is closed - `qa → make-pr` only. `plan → plan-review` is not a row because the plan dispatch already embeds its review loop (a successful plan tick already classifies `work` next); `plan-review → work` and `work → qa`/`make-pr` are not rows because those transitions cross a stage that can fail into human territory. The verdict grammar stays driver-readable: `stage=qa+make-pr`, the verdict is make-pr's, and a driver grepping `PILOT_VERDICT=ADVANCED` keeps working. With `pipeline.qa` off there is nothing to chain, so the switch matters only on repos running the QA stage. Config-table entry: [`flowctl.md`](flowctl.md#config).

On the land side, `land.patienceMinutesAfterReview` (`null` by default) lets the repo choose a review-anchored objection window instead of the push-anchored one: under the default `silence` signal, once the latest automated review is head-current with zero unresolved threads, the patience window is measured from that review event with this key's limit instead of from the last push with `land.patienceMinutes`. It replaces the push window rather than taking the shorter of the two, so relative to today's wait an early review shortens it and a late review lengthens it. It stays opt-in because the push-anchored window is the human-objection grace period - time for a person to read what the bot said and object - and each repo decides how much of that grace it wants once the reviewer has spoken. It refines only the silence gate: the `approve`/`<login>` signals, every other window consumer, and the merge license are unchanged, and a fix push falls back to the push anchor until the bot re-reviews.

Loop internals: [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md), [`ralph.md`](ralph.md) for the hardened harness.

## Unattended chart driving (outside the build loop)

`/flow-next:chart` is **optional pre-capture discovery**, never a stage in the pilot pipeline (`plan → plan-review → work → [qa] → make-pr`). Pilot does not select charts, advance D-IDs, or emit chart briefings.

Drive unattended evidence the same way you drive pilot ticks - host `/loop` or `/goal` on the chart skill itself:

```text
/loop 15m - one tick: run /flow-next:chart <chart-id>.
  If it prints CHART_VERDICT=RESOLVED, continue.
  If CHART_VERDICT=NEEDS_HUMAN, stop (attended decision reached; do not self-answer).
  If CHART_VERDICT=COMPLETE or NO_WORK, stop.
  If CHART_VERDICT=BLOCKED, stop and surface the reason.
```

Contract:

- **One decision per invocation.** Each tick claims at most one D-ID and emits exactly one greppable line: `CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="..."`.
- **Unattended frontier only.** Independent `research` / `probe` / `eval` (and unattended `task`) may fan out as **separate parallel invocations**, each with its own claim, recovery path, and verdict. Never a batch tick that aggregates mixed outcomes.
- **`NEEDS_HUMAN` is terminal for the driver.** Attended types (`prototype`, `interview`) reached under autonomous signals write no answer - the loop parks for a human session.
- **Chart mode creates; work mode resolves.** Charting an idea must not start answering its own decisions. Status mode (`--status`) mutates nothing.

Plain-language steering still works for humans; the exact flags and `flowctl chart` surface are for automation. Full skill contract: [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md); CLI: [`flowctl.md`](flowctl.md#chart).

## In your repo

This page lives in the plugin's doc tree - *outside* the repo you're working in. At use time the host agent reads two files that ship into your project, so the steering recipes are put where agents already look:

- **The usage guide** carries an `## Orchestration & model steering` section, read on demand - the always-loaded CLAUDE.md/AGENTS.md block points agents at it. Agents pull it live via `flowctl usage`, so it is always current with the installed plugin. It contains: the headless `codex exec` / `cursor-agent` / `claude -p` bridge commands and the flow-next shortcuts (`review.backend`, per-task `review:`, prompted-orchestration examples). The bridges run in **every direction** - `claude -p` lets a Codex or Cursor host conduct Claude the same way; any harness that can run Bash can be the conductor.
- **`CLAUDE.md` / `AGENTS.md`** can hold the durable routing block above: `/flow-next:setup` offers, as an optional ceremony step, to scaffold it live - annotated for the CLIs you actually have installed, shown in full before writing, yours to edit after. Marker-fenced so `/flow-next:uninstall` can remove it cleanly.

## What stays fixed

Steering is broad but not unbounded - these hold no matter what the routing table says:

- **Judgment stays with the host.** A bridged child writes code; it never owns git, task state, review verdicts, or decisions.
- **Merge is human-gated** everywhere except the explicitly opted-in land loop (bounded license: `--squash --match-head-commit`, full gate tree first).
- **Verification is independent.** A bridged diff is never trusted on the child's own summary - the host re-runs the gates before `flowctl done`.
- **Escalation beats thrift.** Downgrade defaults are A/B-verified here; when you downgrade a role yourself, watch the first outputs and revert on the first quality miss.

## See also

- [`platforms.md`](platforms.md) - install matrix, Codex model mapping, cross-platform patterns.
- [`flowctl.md`](flowctl.md) - `review.backend` grammar, `spec set-backend`.
- [`running-lean.md`](running-lean.md) - which layers to run at all, what each costs, and the human-driven vs autonomous profiles.
- [`ralph.md`](ralph.md) - autonomous-mode internals (deprecated).
- [`teams.md`](teams.md) - the handover objects that make cross-model hand-offs safe.

# Orchestration & model routing

flow-next is an orchestration layer, not a single-agent workflow. The host agent (Claude Code / Codex / Droid) conducts: it fans work out to tiered subagents, routes reviews to a *different* model family than the writer, optionally drives a second CLI agent through a headless bridge, and runs autonomous build/ship loops. Which model does what is a routing decision — and every routing decision in flow-next is either a parameter or a sentence of intent away. The second kind carries judgment.

The pattern this page serves: use your smartest model to orchestrate and judge, route mechanical or token-hungry work to faster/cheaper models, and pick reviewers from a different family than the writer. flow-next was built in this shape — this page maps the dials.

**None of this is required.** The skills and subagents ship pre-tuned to work well out of the box for everyone — review defaults sensible, the pipeline complete with zero routing config. Steering is a capability, not a prerequisite: reach for the dials below when your model mix, subscriptions, or taste differ from the defaults, and ignore this page entirely until they do. The same doctrine applied to subsystems rather than models — which layers to switch on at all, and what each costs — is [`running-lean.md`](running-lean.md).

## Tiers — what kind of model a job wants

Two words carry the whole routing story. A **tier** is what kind of model a job wants. **Reach** is how the active harness obtains one — the in-session model, an in-host subagent, shelling out to another CLI, or not available.

**This section is the single definition of the tier names.** They are a user-facing interface, chosen once; anywhere else in flow-next that routes work refers back here rather than restating them.

| Tier | What it means |
|---|---|
| **reviewer** | Anything grading work someone else produced. The only tier carrying a family rule: a reviewer from the writer's own family is not an independent verdict. |
| **implementer** | Work handed to another harness. The load-bearing case — plan on the session model, implement somewhere cheaper or faster. Absent, the session model implements. |
| **fast scout** | Mechanical inventory scanning, where the cheapest model is the correct one. |
| **thinking scout** | Analysis that degrades badly on a fast model. |
| **unset** | The default, and the majority: planning, capture, interviews, requirement analysis, every verdict, and the worker run on the session model. This is the never-delegate-judgment doctrine, stated as the default rather than as a special case. |

A fifth name would be a breaking change to a user-facing interface. An **unrecognized tier name is treated as unset**, with one advisory line — never an error.

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

An absent tier means the session model. An unparseable line is ignored with one advisory, never an error. Effort semantics stay the host's — flow-next passes effort through and never translates between vendors' scales. `/flow-next:setup` proposes this block commented out, for you to edit; nothing infers availability into it, and nothing rewrites a block a human has edited.

The block is the durable form of an ad-hoc instruction. Written once, it is read every turn — and an explicit instruction in the moment still wins over it, which is exactly the precedence below.

Worked example, in a consumer's own words:

```text
you conduct + review (frontier, medium effort); implementation goes to
<another model> via <its CLI>, one task per dispatch
```

### Routing precedence

**Routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.**

There is no error surface: the chain terminates at the session model by construction. Agent definitions keep their model field as the **floor** — what applies when nothing overrides — which is why a repo with no routing block behaves exactly as it always has. The review backend is separate: it keeps its own `backend[:model[:effort]]` configuration and its own documented precedence ([Review backends](#review-backends--cross-model-review)).

A model this harness cannot reach — another vendor's identifier, a retired one, one your account lacks — falls back to the session model, says so once, and continues. No probing, no question, no failure.

## Reach — how this harness gets one

Reach is documented **once per harness**, never inside a skill: a skill asks for a tier, and never names a spawn primitive, a CLI flag, or a vendor path. Each page states which mechanisms exist there, which do not, the degradation when one is missing, and how to discover what the harness offers instead of trusting a stored answer.

[`reach/README.md`](reach/README.md) — index and the four questions every page answers · [Claude Code](reach/claude-code.md) · [Codex](reach/codex.md) · [Droid](reach/droid.md) · [Cursor](reach/cursor.md) · [Grok Build](reach/grok-build.md) · [OpenCode](reach/opencode.md) · [generic fallback](reach/generic.md)

An undetectable harness resolves to the generic page and says so. **Discovery beats declaration:** where a harness can list what it offers, ask it — one command beats a stored fact that goes stale.

## Two ways to route

**Skills are prompts executed by the host agent, not compiled code.** That gives you two genuinely different routing methodologies — use both:

| | **Deterministic — parameters** | **Prompted — agentic intelligence** |
|---|---|---|
| What it is | Config keys, flags, env vars, per-spec/per-task fields. Machine-resolved, same answer every time | Policy described in natural language. The host *judges* per item — conditionally, mid-run, against context no parameter can see |
| Example | `flowctl config set review.backend codex` | "Work the three ready specs — decide per spec, by complexity, whether implementation goes out to a codex bridge or stays on the session model" |
| Reach | Exactly the surfaces that ship (below) | Anything the host can do — including capabilities that don't exist as parameters |
| When it wins | Headless/Ralph runs, stable team defaults, reproducibility | Per-item complexity calls, conditional escalation, one-off arrangements, inventing a routing the registry doesn't have |

The two compose: parameters set the floor, prompting steers above it. And either can be made durable by writing it into `CLAUDE.md` / `AGENTS.md` — the host reads your instruction files every session, and flow-next skills inherit them automatically because the host is the one executing them.

### Two layers of steering — session vs machinery

The table above is really two layers with a clean seam, and knowing which layer you are talking to answers most "will this override that?" questions:

- **Session steering** — your prompts and per-task pins. Top of the precedence chain, ephemeral, done the moment the task is done. Saying *"implement via grok-4.6 and review with sol"* just works: the agent runs the grok bridge for the draft and pins sol for the review, and **nothing persists afterward** — pins and defaults resume untouched. Your `CLAUDE.md` routing prose lives in this layer too: deterministic plumbing never reads prose, but the *agent* reads it every turn and feeds explicit values downward, so a `CLAUDE.md` pipeline dominates everything the agent orchestrates by occupying the higher-precedence rung — not by editing config.
- **Machinery steering** — config resolved by deterministic plumbing that never reads prose: `review.backend`, the `models.roles` role map. This is what autonomous loops (pilot, Ralph, land ticks) and unattended gates use when nobody is prompting. Standing changes for autonomous runs belong here, not in prose.

For the models that execute stages, the chain is the one stated above: **routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.** The review backend resolves separately, through its own configuration grammar — see [Review backends](#review-backends--cross-model-review) for that chain; the tiers above never touch it. One consequence worth spelling out: a prompt can steer only the session it is typed in — if you want pilot ticks at 3am to use a different reviewer, that is a config change (`flowctl config set review.backend ...`), because at 3am there is no prompt.

## Deterministic routing — the parameter surfaces

### The host model — the conductor

You pick it in your harness (e.g. `/model`). The host owns everything that requires judgment: gating, task classification, git, review-verdict interpretation, user consent. Workers and resolvers ship with `model: inherit`, so the session model *is* the implementation model unless you route implementation out over a bridge (below). Practical consequence: a frontier session model gives you a frontier planner *and* frontier workers; dropping the session model for a mechanical spec drops both.

### Agent defaults — the floor

Bundled agents carry a model field grouped by task shape (see `agents/*.md` frontmatter). These are **defaults**, not pins: they are the third rung of the routing precedence, so an explicit argument or your routing block overrides them, and a repo with neither behaves exactly as shipped.

| Agent group | Agents | Why |
|------|--------|-----|
| fast (`haiku`) | prime's pillar scanners (build/env/security/testing/tooling/workflow/observability) + memory-scout | mechanical scan-and-report |
| judgment (`sonnet`) | planning scouts (repo/context/spec/docs/github/practice, …), flow-gap-analyst, plan-sync | read-and-judge, bounded scope |
| heavy (`opus`) | quality-auditor | adversarial audit |
| `inherit` | worker, pr-comment-resolver | implementation follows the session model |

The Codex mirror maps these to `gpt-5.5` / `gpt-5.4-mini` at sync time (`scripts/sync-codex.sh` `map_model`). Precedence at regen: env (`CODEX_MODEL_INTELLIGENT` / `CODEX_MODEL_FAST`) > role-map pins (`models.roles.scoutIntelligent.codex` / `scoutFast.codex` when present in the repo `.flow/config.json`) > those baselines. The worker keeps `inherit` on both platforms (your session model rules); an OPT-IN sync-time pin (`CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER`, recommended `gpt-5.6-terra` @ `medium`) lets Codex-host work threads ride the efficient tier. Details: [`platforms.md`](platforms.md).

**Cursor host:** canonical `agents/*.md` family aliases (`haiku` / `sonnet` / `opus`) resolve to **inherit** (the session model) when running on a Cursor host. Caller-side model pins (Cursor slugs like `claude-opus-4-8-thinking-high`) are the escape hatch for picking a specific model. There is no alias-to-slug rewrite mechanism and none is planned.

### Role map: the one place pins rot (fn-115)

Hardcoded model pins used to scatter across the registry, triage defaults, and sync-codex scout constants. They all rot as providers ship tiers. The **role map** is the single config surface that is allowed to hold those pins:

```bash
flowctl config set models.roles.fastJudge.codex gpt-5.6-luna
flowctl config set models.roles.review.codex gpt-5.6-sol:medium
flowctl config set models.roles.scoutFast.codex gpt-5.6-luna
flowctl config set models.roles.scoutIntelligent.codex gpt-5.5
flowctl config set models.verifiedAt 2026-07-21
```

Roles name **jobs** (`fastJudge` / `review` / `scoutFast` / `scoutIntelligent`), not call sites. Resolution order extends the existing review precedence: explicit CLI / per-task pin > env > role map > registry baseline. Registry ladders stay as availability fallbacks (they heal pin-too-new); the role map heals pin-too-old.

**Refresh path is the setup ceremony**, not Python judgment. `/flow-next:setup` probes installed CLIs, the host agent judges which tiers fit each role, proposes Accept / Stamp-only / Skip, and writes accepted pins + `models.verifiedAt`. When `verifiedAt` is older than ~90 days, `flowctl status` prints one non-blocking line. Skills resolve pins with:

```bash
flowctl models resolve <role> [--backend codex] [--json]
```

Read a role pin through `models resolve`, never `config get`: a merged config default bypasses the role map.

**Known Codex limitation (Jul 2026):** on GPT-5.6 Sol / Multi-Agent V2 builds, per-spawn model steering is unreliable end to end - `spawn_agent` stripped `model`/`reasoning_effort`/`agent_type` from its schema (openai/codex#31814, partially restored by #32749; `agent_type` still missing per #32782), explicit overrides are silently dropped when the agent carries a role layer (#33268), and role-profile application is not verifiable (#33314). Until those settle, the ROBUST way to steer a different model from a Codex host is the **same-family self-bridge**: `codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium "<self-contained prompt>"` - a fresh process taking `-m` on the command line, immune to the spawn_agent path entirely. Caveats: the child needs process-spawn + network inside the parent sandbox, and keep the child prompt flat (a child that spawns MAv2 subagents of its own can return undecodable results, #33267).

### Review backends — cross-model review

> **Optional.** flow-next runs fully without this; `review.backend` is unset by default and reviews run in-host. It costs an out-of-host review pass per review round, a second CLI installed and authenticated, and a fix-and-re-review loop that can run up to `review.maxIterations` rounds; turn it on when agent-written diffs get merged without a human reading them line by line, or invoke it manually with `/flow-next:impl-review` on the changes that warrant it. See [`running-lean.md`](running-lean.md#cross-model-review-backend).

The review subsystem is the most routable surface. Spec grammar `backend[:model[:effort]]`, registry `rp | codex | copilot | cursor | host | none` (`host` is bare-only — no model/effort rungs). The three CLI review backends (`codex` / `copilot` / `cursor`) are `BACKEND_REGISTRY` entries driving one shared `cmd_backend_review` pipeline (fn-112); genuine variance is hooks, not cloned commands.

```bash
flowctl config set review.backend codex                    # project default
flowctl config set review.backend cursor:composer-2.5     # cursor folds effort into the model name
flowctl config set review.backend codex:gpt-5.4:xhigh     # explicit model + effort
flowctl config set review.maxIterations 6                 # review-round cap (env MAX_REVIEW_ITERATIONS wins; >= 1, human-only under Ralph)
```

Precedence (highest wins): per-task `review:` / per-spec `default_review` → `FLOW_REVIEW_BACKEND` → `.flow/config.json` `review.backend` → backend-specific env → registry default. A single task can pin a different reviewer than the project default and the override routes end-to-end. The `cursor` backend unlocks reviewer models the others can't reach in one place (`gpt-5.6-sol-high` at 1M context — the default, `gpt-5.6-terra`/`-luna`, `grok-4.6-high` / `grok-4.5-high` (fast cross-family pass), `composer-2.5`, the `gpt-5.3-codex` family, `claude-opus-5-thinking-high`, `claude-opus-4-8-thinking-high`) on your existing Cursor subscription. Full grammar + registry: [`flowctl.md`](flowctl.md#review-backend).

**The review prompt carries identities, not payloads (fn-169).** A reviewer runs
in your checkout with a shell, so it is an executor like any other agent: flow-next
hands it the rubric, a `<base-sha>..<head-sha>` range, `git diff --numstat --no-renames`
as the exact scope map, and repo-relative spec/task paths — then the reviewer fetches
what it needs at whatever depth each hunk warrants. It does **not** ship the diff
body, the spec text, or the task specs. That is not a size optimisation with a
quality cost; the payload was the quality cost. The diff body used to be capped at
50 KB, so on a 495 KB change the reviewer received ~10% of the evidence its verdict
rested on and fetched the rest anyway. `--numstat --no-renames` matters more than it
looks: plain `--stat` abbreviates paths (`.../pr-cognitive-aid/.write.lock`) and
plain `--numstat` collapses renames into `{old => new}`, and a scope map you cannot
resolve to paths is not a scope map.

Two consequences are load-bearing rather than incidental. First, **a prompt-payload
fitter or truncator is evidence the payload is wrong** — flow-next kept exactly one
size guard, `CURSOR_ARGV_TRANSPORT_MAX`, and it is named as *transport* because
`cursor-agent` takes its prompt as a positional argv argument and Windows
`CreateProcessW` has a hard limit. It refuses loudly; it never trims. Second, an
evidence read that FAILS aborts before a review round is reserved, because with
nothing embedded an empty scope map is not a degraded review, it is no review.

**Prior findings ride the session, not the prompt (fn-169).** Re-reviews resume the
reviewer's own session, so it already holds the findings it made — the round sends
the shrink-only contract and the reply grammar, and re-renders nothing. Injection is
the fallback: if the resume fails, flow-next rebuilds the prompt *with* the findings
and dispatches fresh. The order is deliberate — a lean prompt reaching a
context-free session would be a fresh blind review with the priors dropped, which is
the runaway this machinery exists to stop. Two-phase resume is enabled for `codex`,
whose resume is measured; `copilot` (whose `--resume` is create-or-resume via a
marker) and `cursor` inject unconditionally. `host` always injects — it has no
session by design, every re-review being a fresh subagent. Injecting when it was
unnecessary costs bytes; not injecting after a silent resume failure costs a blind
review, so injection is the default everywhere it is not provably unnecessary.

**Rule of thumb: the model that writes is never the model that reviews.** Route the reviewer to a different family than your session model and blind spots stop being correlated.

**Ambient-instruction contamination + persona override (fn-90, extended to codex by fn-187 / #331).** A reviewer subprocess can inherit instructions that were never meant for it, and each backend has its own channel:

- **cursor** - `cursor-agent` has **no system-prompt mechanism**: the flow-next reviewer rubric travels as a plain user prompt *on top of* Cursor's own built-in persona (which carries its OWN review rubric and an end-to-end-thoroughness bias), and `cursor-agent` auto-attaches the workspace `AGENTS.md` / `CLAUDE.md`, skill catalogs, and MCP instruction blocks. That ambient guidance dilutes the in-scope anchor and biases the reviewer toward always-produce-findings - an amplifier of review-loop non-convergence, not the root cause. There is no cursor CLI knob to suppress the auto-attach.
- **codex** - `codex exec` auto-loads the host repo's project doc (`AGENTS.md`); in a repo whose `AGENTS.md` routes all work through the flow-next skills, the reviewer adopts that role and re-dispatches the review at itself instead of performing it (#331 route A - suppressed at the argv level with `-c project_doc_max_bytes=0` on both the fresh and resume dispatch). With the flow-next codex plugin installed, the reviewer can also read the plugin's own coordinator skills ("never self-declares a verdict") and obediently withhold the verdict tag (#331 route B - no CLI knob exists).

On both backends flow-next prepends an explicit **persona-override preamble** on every review path: it declares that any ambient rubric/persona/instruction from the environment - built-in persona, auto-attached `AGENTS.md`/`CLAUDE.md`, skill catalogs, MCP blocks - is *superseded*, and the ONLY rubric + verdict contract is the flow-next one that follows. Repo-specific review invariants belong in `.flow/criteria.md` (standing G-IDs), which rides the review prompts themselves and reaches every reviewer regardless of backend - `AGENTS.md` is host-agent operating instructions, not a review-criteria channel, and a reviewer that inherits it returns no verdict at all rather than a stricter one (#331). Documented, not configurable; it rides automatically on `review.backend cursor:*` and `codex`. A review that still completes with no verdict is journaled as `missing_verdict` (not a transport failure class), and a streak of those terminates with instruction-contamination guidance instead of "repair the backend". The structured-findings ratchet and deterministic convergence terminals (unchanged-artifact refusal, early escalation when the reviewer explicitly marks the same finding `not-fixed` in two consecutive rounds, the round cap, and reviewer-emitted `NEEDS_HUMAN`) apply to every backend - see [`flowctl.md`](flowctl.md#codex-impl-review).

### Implementation offload — the bridge route

Offloading the token-heavy part (writing code) to a second CLI is a **routing decision you write, not a subsystem you configure**. There is no packaged delegation mode and no `work.delegate*` config: you drive the other CLI through a headless bridge, either ad hoc in the session or as standing policy in `CLAUDE.md` / `AGENTS.md`.

```bash
codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium "<self-contained prompt>"
cursor-agent --model <slug> --force "<self-contained prompt>"
claude -p "<self-contained prompt>"     # the same bridge in reverse, from a Codex/Cursor host
```

Two rules survive from the packaged path and are not optional:

- **The bridged child writes code; the host keeps git, judgment, and the verdict.** The child never commits, never decides scope, never issues a review verdict, and never spawns a bridge of its own. Drop this and a bridge recipe becomes an unbounded second agent.
- **Which tier to bridge to:** on well-specified work a value-tier implementer matches a strong-tier one on correctness at roughly two-thirds the wall clock, so send clear, well-scoped tasks to the value tier and escalate to the strong tier only for genuinely gnarly ones. Spec quality is what makes the trade safe — a vague brief burns the saving on rework.

Full recipes (including the thin-wrapper pattern for unattended loops): the usage guide's `## Orchestration & model steering` section — `flowctl usage`, or `.flow/usage.md` in copy-mode repos. Make it durable by writing the routing into your instruction file: [Durable routing](#durable-routing--a-model-table-in-claudemd).

### Per-spec backend fields — external orchestrators

The data model carries routing even where flow-next itself doesn't consume it: `flowctl spec set-backend fn-1 --impl codex:gpt-5.4 --review claude:opus --sync claude:haiku` sets per-spec impl/review/sync backend specs for orchestration products built on top of flow-next (e.g. control planes that dispatch one CLI per spec). See [`flowctl.md`](flowctl.md#spec-set-backend).

## Prompted orchestration — routing with judgment

This is the mode parameters can't reach: the host is an intelligent orchestrator, so routing policy can be *conditional* and *per-item*, decided against the actual work rather than fixed up front.

**Per-item complexity routing** — the host classifies, then routes:

```text
Work through the three ready specs. Decide per spec, based on complexity,
how the work stage runs: anything touching auth or the migration you
implement yourself on the session model; plain CRUD goes out to a codex exec
bridge. Reviews come from codex either way.
```

**Focus and scope steering** — instruction the skill never anticipated, read as intent:

```text
/flow-next:plan fn-12 --depth=deep — focus the research on the migration path; I care about rollback
/flow-next:interview fn-12 — push hard on failure modes and operational edges, skip UI polish
/flow-next:work fn-12 — the UI tasks stay with you; send the API plumbing out to a codex bridge
```

**Conditional escalation** — routing that reacts to outcomes:

```text
Run /flow-next:work fn-12 and bridge implementation to codex exec. If a task's
review comes back NEEDS_WORK twice, stop bridging that task and implement it
yourself on the session model.
```

**Prompting a capability into existence** — the registry has no `fable` review backend; that didn't stop this repo's own eval loop from running Fable-reviewed rounds:

```text
/flow-next:plan-review fn-12 — don't use the configured backend; spawn a
fresh-context subagent on the session model with the same review criteria,
and feed its verdict into the fix loop like any other reviewer.
```

Backends, reviewers, and bridged implementers are prompts plus plumbing — when a rung you want is missing, describe it and the host builds the arrangement on the spot. The deterministic flags (`--review=cursor:composer-2.5`, `--depth=short`) still work inline for the parts that *are* parameterized; prompting composes around them.

## Field patterns, mapped to flow-next

The orchestration patterns that emerged in the wild through mid-2026 all have a direct flow-next expression — most need one config key or one sentence:

| Pattern from the field | The idea | flow-next expression |
|------------------------|----------|----------------------|
| **Orchestrator → executor** | The frontier model plans and judges; a cheaper, highly steerable model (GPT-5.5 via the Codex CLI, on the sub you already pay for) writes the code | A `codex exec` bridge recipe, ad hoc or as standing prose in `CLAUDE.md`. Host keeps gating/git/review; the bridged child writes code |
| **Orchestrator → reader** | Token-hungry, low-judgment reads (codebase analysis, doc sweeps) run on fast models that report summaries back — the orchestrator never holds the raw tokens | Already the default: planning scouts and prime scanners run on the fast tiers and return digests. Add `/flow-next:map` for token-efficient exploration |
| **Cross-family reviewer** | The model that writes is never the model that reviews — uncorrelated blind spots | `review.backend codex` / `cursor:composer-2.5` / `copilot:...` — per-task `review:` pins exceptions |
| **Effort discipline** | Run the orchestrator at high, not max — top effort tiers are token furnaces with flat-or-worse output on routine work | Session effort is yours; a bridged child takes its effort inline (`-c model_reasoning_effort=medium` is the recommended floor — raise it for gnarly tasks) |
| **Token-hungry offload** | Computer use, live-app verification, bulk analysis go to other models/agents; results come back as evidence | `/flow-next:qa` drives the app in its own context and files P0/P1/P2 findings; workers run fresh-context and return receipts |

## A proven default pipeline

One controlled pipeline eval (2026-07-14: a hidden 39-check oracle suite for the work stage, a planted-bug review eval at n=3 reps per arm with matched reasoning efforts, dual cross-family blind judges for plans) produced a concrete default routing. It is one task's worth of evidence - motivation, not a guarantee - but it is the shape this repo now runs.

The roles are **model-per-role, not host-relative**: the bridges run in both directions (`codex exec` reaches GPT from a Claude host, `claude -p` reaches Claude from a Codex host), so the recommended model for each role is the same everywhere - only the *reach mechanism* differs by host.

Model-generation note (2026-07-24, effort pin added 2026-07-25): Claude Opus 5 shipped after this eval - near-Fable intelligence at half the price, same $5/$25 pricing as Opus 4.8. On Claude-family hosts it is now the recommended tier for the "session frontier model" rows below (Plan, final gate), with Fable 5 as the escalation rung rather than the default. Run Opus 5 at MEDIUM effort: its own model card's FrontierCode curve peaks at medium and degrades through high/xhigh (Fig 8.4.A/B), and a full opus-5@medium-conducted pilot-to-land run on this repo (fn-122, 2026-07-25) chained cleanly end to end. The eval numbers stay attributed to the models actually measured.

| Role | Model | Why | Reach from a Claude Code host | Reach from a Codex host |
|------|-------|-----|-------------------------------|-------------------------|
| Plan (spec authoring: capture / interview / plan / plan-review critique) | Session frontier model | Two cross-family blind judges ranked frontier plans clearly ahead; raising effort on a weaker planner did not close the gap | Session-native | Session-native * |
| Plan-review | Cross-family frontier | Uncorrelated blind spots on the highest-leverage artifact | `--review=codex` / `review.backend codex` | `review.backend` to a non-GPT family (e.g. `cursor:...`) |
| Work (implementation) | `gpt-5.6-terra` @ `medium` | Matched `gpt-5.6-sol` on hidden-suite correctness at ~2/3 wall-clock on frontier-authored specs; effort above medium was pure overhead | `codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium` bridge; session model natively | the same self-bridge (robust today); session model natively; opt-in sync-time pin `CODEX_MODEL_WORKER=gpt-5.6-terra` once MAv2 profile application is trustworthy |
| Impl-review, first pass | Cross-family from the writer - `gpt-5.6-sol` @ `high` when the writer is Claude-family | 12/12 recall on planted bugs, 0 false positives, fastest reviewer in the fleet (103s mean) | `review.backend codex` (pin `codex:gpt-5.6-sol:high`) - the session writes, sol reviews; no codex CLI? `cursor:gpt-5.6-sol-high` reaches sol through cursor | The worker writes GPT (terra), so sol would be SAME-family: route the first pass to a non-GPT reviewer instead - packaged rungs `review.backend copilot:claude-opus-4.5` / `cursor:claude-opus-5-thinking-high` (or `cursor:claude-opus-4-8-thinking-high`; cursor also carries `claude-fable-5-thinking-high` — NO ZDR — and, for the reverse direction, `gpt-5.6-sol-high`), or Claude Code ad hoc via the `claude -p` reverse bridge (no packaged rung; prefer opus/sonnet targets - fable via `claude -p` can hit CLI credit limits) |
| Impl-review, final gate | Session frontier model | Only the frontier tier volunteered correct severity tiering and blast-radius judgment unprompted | Session-native (the host interprets the verdict; escalate disagreements to it) | Session-native |

\* Spec authoring is **session-native by design** — capture, interview, and plan are inline skills, so the session model is who writes and refines every spec - there is no packaged cross-family plan rung. Ad-hoc bridging works (`claude -p` can author a plan from a Codex host) but frontier-Claude via `claude -p` can hit CLI credit limits on plan-sized prompts (observed 2026-07-14); plan on whatever frontier model your session runs.

Notes that keep the table honest:

- **Single subscription? The table still reads correctly.** Most orgs run ONE harness subscription. Every row degrades to "the session model" and the pipeline works exactly as shipped - multi-model routing is optional garnish, never a prerequisite.
- **`gpt-5.6-luna` @ `xhigh`** is the equal-recall alternative for the first-pass reviewer (12/12) at ~2.5x the time; luna-medium is the budget implementer alternative (same hidden-suite correctness, tightest code, more tool-loop round-trips).
- **`grok-4.x` is a classic-bug quick pass ONLY - never the gate.** grok-4.5 missed the eval's subtle latent bug in all 3 runs; fine as a cheap extra pass, but a ship decision must not rest on it. grok-4.6 (2026-08-12) has not been re-evaled here - its independent numbers argue for keeping this posture (AA-Omniscience: invents ~1/3 of the time when it doesn't know; Terminal-Bench v3 26%), even though its supervised-editing scores and real-user reports improved markedly.
- Build-tier models are excluded from review roles entirely (in the same eval one missed a planted bug, another returned a false all-clear).
- **"Cross-family" is measured from the WRITER, not the host.** sol-high's 12/12 was earned reviewing Claude-family-written code; when your writer is GPT (e.g. the Codex mirror's terra-pinned worker), a GPT reviewer re-correlates the blind spots - pick the reviewer from whichever family did NOT write the diff.

### The wrapper pattern - self-healing bridges for unattended loops

Raw bridge calls have a silent-failure class: outside a trusted git directory, `codex exec` refuses in about a second with the error only in its log, and `cursor-agent` blocks on an interactive workspace-trust prompt, then exits "successfully" with empty output. An interactive host sees the stderr and just fixes it; an **autonomous loop dies silently**. The pattern that closed this in the eval: wrap the bridge in a thin fast-tier subagent (sonnet-class) instead of calling it raw. The wrapper composes the self-contained prompt, runs the bridge, verifies output is non-empty/parseable, repairs the environment if not, and retries once. Output quality was identical to raw calls.

Two rules are load-bearing:

- **The wrapper MUST run the bridge in the foreground** - one blocking Bash call. A backgrounded bridge loses the completion signal and the wrapper idles forever on a finished (or silently dead) process.
- **The self-heal license covers environment and flags only, never judgment.** In scope: git trust (`--skip-git-repo-check`, `git init` in a scratch dir), sandbox flags, stale model ids, empty-output retry. Out of scope: rewriting the task prompt, interpreting review verdicts, or switching models on quality grounds - judgment stays with the host.

This is a documented pattern, not a shipped agent type - the bridge recipes live in the usage guide's `## Orchestration & model steering` section (`flowctl usage`; in copy-mode repos also on disk at `.flow/usage.md`). Interactive sessions don't need it.

### Raw-bridge review prompts - demand severity tiers

Applies to **ad-hoc bridge reviews only** - a hand-rolled `codex exec` review whose output a human reads directly (the usage.md recipes). When you write one, put two things in the prompt:

- **P0-P3 severity tiers plus spec-grounded verdicts**, so an edge-case finding does not flip a ship gate. Reviewers reliably flag spec-gray edges as bugs (in the eval, behavior explicitly licensed by a plan amendment was reported as a defect by every reviewer) - severity tiers and "cite the spec line" are what keep those findings informative instead of gate-flipping.
- Optionally **a minimal suggested fix and blast radius per finding** when no fix loop follows the review. Control runs showed this artifact is prompt-shaped: models produce it when the prompt demands it and omit it when not asked.

The **packaged** `/flow-next:impl-review` prompt is deliberately NOT changed to this shape: its find-vs-fix split (the reviewer returns findings; the internal fix loop investigates and fixes, with validator and iteration caps) is by design, and its rubric already carries confidence anchors and introduced-vs-pre-existing classification. Deep-pass/validator merge math is autonomous-only (fn-113.4): under `FLOW_RALPH` / `REVIEW_RECEIPT_PATH` / `FLOW_AUTONOMOUS` flowctl mutates the receipt; interactive surfaces raw findings and the host judges.

## Durable routing — a model table in CLAUDE.md

The emergent pattern (mid-2026): a standing "which model for what" section in your agent instructions — a ranking of the models you can reach plus routing rules. This is **prompted orchestration made durable**: the table is interpreted by intelligence, not parsed by a config loader. The host reads it every session and applies it *with judgment* when it dispatches subagents, picks reviewers, or decides to bridge implementation out — which is exactly why the rules grant standing permission to escalate.

flow-next ships this as a canonical scaffold — [`../skills/flow-next-setup/templates/model-routing-snippet.md`](../skills/flow-next-setup/templates/model-routing-snippet.md): a scores table (cost / speed / intelligence / taste) over the session model, `gpt-5.6` (sol/terra), `grok-4.5`, `composer-2.5`, and a fast Claude tier, plus how-to-apply rules and the exact flow-next surface each route drives (the worker, the bridge recipes, review backends, scouts, the thin-wrapper). `/flow-next:setup` offers to write it into your `CLAUDE.md`/`AGENTS.md` live, annotated for the CLIs you actually have installed. The shape, illustrated (cost = subscription-quota lightness, not list $/token; speed = at default reasoning effort):

```markdown
| model                    | cost | speed | intelligence | taste |
|--------------------------|------|-------|--------------|-------|
| session model (frontier) | 2    | 2     | 10           | 9     |
| gpt-5.6-sol              | 8    | 5     | 9            | 6     |
| grok-4.5                 | 9    | 9     | 7            | 5     |
| composer-2.5             | 9    | 10    | 6            | 6     |

- Defaults, not limits — escalate to a smarter model when output misses the bar.
- Bridged implementation → gpt-5.6-terra @ medium (escalate to gpt-5.6-sol when a task looks gnarly); fast/cheap first-draft implementation → grok-4.5 (`grok -p`); cheap bulk reads → gpt-5.6-terra; reviews cross-family; user-facing needs taste ≥ 7.
- Graceful degrade: a routed CLI that is missing or errors → fall back to the session model.
```

The template is the single source — edit your scaffolded copy freely; the excerpt above only shows the shape. Role labels are durable; model IDs are volatile. Write the table in terms of roles, re-rank as the frontier moves, and the routing rules survive every model generation.

## Chaining the loops

Pilot and land end every tick with machine-readable verdict lines precisely so a host driver can compose them. Pilot never merges and never invokes land (consent boundary); the *driver* routes between them:

```text
/loop 30m — one tick: run /flow-next:pilot --review=codex.
  If it prints PILOT_VERDICT=DEFERRED_TO_LAND, run /flow-next:land in the same tick.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK, or on any NEEDS_HUMAN.
```

`DEFERRED_TO_LAND` exists exactly for this hand-off — every remaining spec has an open PR that land, not pilot, owns. Compose model routing into the same driver and you have a multi-model spec-to-merged-PR pipeline in one prompt:

```text
/loop 30m — one tick: run /flow-next:pilot --review=codex --depth=deep.
  If PILOT_VERDICT=DEFERRED_TO_LAND, run /flow-next:land in the same tick.
  Bridge implementation tasks to codex exec on gpt-5.6-terra,
  keep UI tasks on the session model, reviews come from codex.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK,
  or on any NEEDS_HUMAN.
```

Loop internals: [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md), [`ralph.md`](ralph.md) for the hardened harness.

## Unattended chart driving (not a pilot stage)

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

This page lives in the plugin's doc tree — *outside* the repo you're working in. At use time the host agent reads two files that ship into your project, so the steering recipes are put where agents already look:

- **The usage guide** carries an `## Orchestration & model steering` section, read on demand - the always-loaded CLAUDE.md/AGENTS.md block points agents at it. In plugin mode (fn-121, Claude Code) agents pull it live via `flowctl usage` (always current with the installed plugin); in copy-mode repos it is also installed on disk as `.flow/usage.md`. It contains: the headless `codex exec` / `cursor-agent` / `claude -p` bridge commands and the flow-next shortcuts (`review.backend`, per-task `review:`, prompted-orchestration examples). The bridges run in **every direction** — `claude -p` lets a Codex or Cursor host conduct Claude the same way; any harness that can run Bash can be the conductor.
- **`CLAUDE.md` / `AGENTS.md`** can hold the durable model-routing table above: `/flow-next:setup` offers, as an optional ceremony step, to scaffold it live — annotated for the CLIs you actually have installed, shown in full before writing, yours to edit after. Marker-fenced so `/flow-next:uninstall` can remove it cleanly.

## What stays fixed

Steering is broad but not unbounded — these hold no matter what the routing table says:

- **Judgment stays with the host.** A bridged child writes code; it never owns git, task state, review verdicts, or decisions.
- **Merge is human-gated** everywhere except the explicitly opted-in land loop (bounded license: `--squash --match-head-commit`, full gate tree first).
- **Verification is independent.** A bridged diff is never trusted on the child's own summary — the host re-runs the gates before `flowctl done`.
- **Escalation beats thrift.** Downgrade defaults are A/B-verified here; when you downgrade a role yourself, watch the first outputs and revert on the first quality miss.

## See also

- [`platforms.md`](platforms.md) — install matrix, Codex model mapping, cross-platform patterns.
- [`flowctl.md`](flowctl.md) — `review.backend` grammar, the `models.roles` role map, `spec set-backend`.
- [`running-lean.md`](running-lean.md) — which layers to run at all, what each costs, and the human-driven vs autonomous profiles.
- [`ralph.md`](ralph.md) — autonomous-mode internals (deprecated).
- [`teams.md`](teams.md) — the handover objects that make cross-model hand-offs safe.

# Orchestration & model routing

flow-next is an orchestration layer, not a single-agent workflow. The host agent (Claude Code / Codex / Droid) conducts: it fans work out to tiered subagents, routes reviews to a *different* model family than the writer, optionally delegates implementation to a second CLI agent, and runs autonomous build/ship loops. Which model does what is a routing decision — and every routing decision in flow-next is either a parameter or a sentence of intent away. The second kind carries judgment.

The pattern this page serves: use your smartest model to orchestrate and judge, route mechanical or token-hungry work to faster/cheaper models, and pick reviewers from a different family than the writer. flow-next was built in this shape — this page maps the dials.

**None of this is required.** The skills and subagents ship pre-tuned to work well out of the box for everyone — model tiers A/B-verified before every downgrade, review defaults sensible, the pipeline complete with zero routing config. Steering is a capability, not a prerequisite: reach for the dials below when your model mix, subscriptions, or taste differ from the defaults, and ignore this page entirely until they do.

## Two ways to route

**Skills are prompts executed by the host agent, not compiled code.** That gives you two genuinely different routing methodologies — use both:

| | **Deterministic — parameters** | **Prompted — agentic intelligence** |
|---|---|---|
| What it is | Config keys, flags, env vars, per-spec/per-task fields. Machine-resolved, same answer every time | Policy described in natural language. The host *judges* per item — conditionally, mid-run, against context no parameter can see |
| Example | `flowctl config set review.backend codex` | "Work the three ready specs — decide per spec, by complexity, whether implementation is delegated or stays on the session model" |
| Reach | Exactly the surfaces that ship (below) | Anything the host can do — including capabilities that don't exist as parameters |
| When it wins | Headless/Ralph runs, stable team defaults, reproducibility | Per-item complexity calls, conditional escalation, one-off arrangements, inventing a routing the registry doesn't have |

The two compose: parameters set the floor, prompting steers above it. And either can be made durable by writing it into `CLAUDE.md` / `AGENTS.md` — the host reads your instruction files every session, and flow-next skills inherit them automatically because the host is the one executing them.

## Deterministic routing — the parameter surfaces

### The host model — the conductor

You pick it in your harness (e.g. `/model`). The host owns everything that requires judgment: gating, task classification, git, review-verdict interpretation, user consent. Workers and resolvers ship with `model: inherit`, so the session model *is* the implementation model unless you delegate (below). Practical consequence: a frontier session model gives you a frontier planner *and* frontier workers; dropping the session model for a mechanical spec drops both.

### Subagent tiers

The bundled agents are pre-tiered by task shape (each A/B-verified before downgrade — see `agents/*.md` frontmatter):

| Tier | Agents | Why |
|------|--------|-----|
| fast (`haiku`) | prime's pillar scanners (build/env/security/testing/tooling/workflow/observability) + memory-scout | mechanical scan-and-report |
| judgment (`sonnet`) | planning scouts (repo/context/spec/docs/github/practice, …), flow-gap-analyst, plan-sync | read-and-judge, bounded scope |
| heavy (`opus`) | quality-auditor | adversarial audit |
| `inherit` | worker, pr-comment-resolver | implementation follows the session model |

The Codex mirror maps these to `gpt-5.5` / `gpt-5.4-mini` at sync time (`scripts/sync-codex.sh` `map_model`, overridable via `CODEX_MODEL_INTELLIGENT` / `CODEX_MODEL_FAST`). Details: [`platforms.md`](platforms.md).

### Review backends — cross-model review

The review subsystem is the most routable surface. Spec grammar `backend[:model[:effort]]`, registry `rp | codex | copilot | cursor | none`:

```bash
flowctl config set review.backend codex                    # project default
flowctl config set review.backend cursor:composer-2.5     # cursor folds effort into the model name
flowctl config set review.backend codex:gpt-5.4:xhigh     # explicit model + effort
```

Precedence (highest wins): per-task `review:` / per-spec `default_review` → `FLOW_REVIEW_BACKEND` → `.flow/config.json` `review.backend` → backend-specific env → registry default. A single task can pin a different reviewer than the project default and the override routes end-to-end. The `cursor` backend unlocks reviewer models the others can't reach in one place (`gpt-5.6-sol-high` at 1M context — the default, `gpt-5.6-terra`/`-luna`, `composer-2.5`, the `gpt-5.3-codex` family, `claude-opus-4-8-thinking-high`) on your existing Cursor subscription. Full grammar + registry: [`flowctl.md`](flowctl.md#review-backend).

**Rule of thumb: the model that writes is never the model that reviews.** Route the reviewer to a different family than your session model and blind spots stop being correlated.

**Cursor backend — ambient-injection caveat + persona override (fn-90).** `cursor-agent` has **no system-prompt mechanism**: the flow-next reviewer rubric travels as a plain user prompt *on top of* Cursor's own built-in persona (which carries its OWN review rubric and an end-to-end-thoroughness bias), and `cursor-agent` auto-attaches the workspace `AGENTS.md` / `CLAUDE.md`, skill catalogs, and MCP instruction blocks into the reviewer's context. That ambient guidance dilutes the in-scope anchor and biases the reviewer toward always-produce-findings — a real contributor to review-loop non-convergence (it *amplifies*, it is not the root cause). There is no CLI knob to suppress the auto-attach, so flow-next prepends an explicit **persona-override preamble** on every cursor review path: it declares that any ambient rubric/persona/severity-ordering from the environment is *superseded* and the ONLY rubric + verdict contract is the flow-next one that follows. This is documented, not configurable — nothing to set; it rides automatically on `review.backend cursor:*`. (The convergence ratchet + deterministic cap that actually *fix* the runaway apply to all backends — see [`flowctl.md`](flowctl.md#codex-impl-review).)

### Implementation delegation — `work` → `codex exec`

Opt-in offload of the token-heavy part (writing code) to a second CLI while the host keeps all judgment:

```bash
flowctl config set work.delegate codex          # activation predicate is exactly the string "codex"
flowctl config set work.delegateModel gpt-5.5   # default
flowctl config set work.delegateEffort medium   # none|low|medium|high|xhigh floor
```

Or per-invocation: `/flow-next:work fn-12 delegate:codex`. The host retains gating, classification, git ownership, review, and commit; `codex exec` writes code and is forbidden from git and decisions. OFF by default, one-time consent-gated, circuit-breakered, with an independent verification backstop (the worker runs tests on the delegated diff even with `REVIEW_MODE=none`). Full contract: [`codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md).

### Per-spec backend fields — external orchestrators

The data model carries routing even where flow-next itself doesn't consume it: `flowctl spec set-backend fn-1 --impl codex:gpt-5.4 --review claude:opus --sync claude:haiku` sets per-spec impl/review/sync backend specs for orchestration products built on top of flow-next (e.g. control planes that dispatch one CLI per spec). See [`flowctl.md`](flowctl.md#spec-set-backend).

## Prompted orchestration — routing with judgment

This is the mode parameters can't reach: the host is an intelligent orchestrator, so routing policy can be *conditional* and *per-item*, decided against the actual work rather than fixed up front.

**Per-item complexity routing** — the host classifies, then routes:

```text
Work through the three ready specs. Decide per spec, based on complexity,
how the work stage runs: anything touching auth or the migration you
implement yourself on the session model; plain CRUD is delegated to codex
(delegate:codex). Reviews come from codex either way.
```

**Focus and scope steering** — instruction the skill never anticipated, read as intent:

```text
/flow-next:plan fn-12 --depth=deep — focus the research on the migration path; I care about rollback
/flow-next:interview fn-12 — push hard on failure modes and operational edges, skip UI polish
/flow-next:work fn-12 — the UI tasks stay with you; delegate the API plumbing to codex
```

**Conditional escalation** — routing that reacts to outcomes:

```text
Run /flow-next:work fn-12 with delegate:codex. If a task's review comes back
NEEDS_WORK twice, stop delegating that task and implement it yourself on the
session model.
```

**Prompting a capability into existence** — the registry has no `fable` review backend; that didn't stop this repo's own eval loop from running Fable-reviewed rounds:

```text
/flow-next:plan-review fn-12 — don't use the configured backend; spawn a
fresh-context subagent on the session model with the same review criteria,
and feed its verdict into the fix loop like any other reviewer.
```

Backends, reviewers, and delegates are prompts plus plumbing — when a rung you want is missing, describe it and the host builds the arrangement on the spot. The deterministic flags (`--review=cursor:composer-2.5`, `delegate:codex`, `--depth=short`) still work inline for the parts that *are* parameterized; prompting composes around them.

## Field patterns, mapped to flow-next

The orchestration patterns that emerged in the wild through mid-2026 all have a direct flow-next expression — most need one config key or one sentence:

| Pattern from the field | The idea | flow-next expression |
|------------------------|----------|----------------------|
| **Orchestrator → executor** | The frontier model plans and judges; a cheaper, highly steerable model (GPT-5.5 via the Codex CLI, on the sub you already pay for) writes the code | `flowctl config set work.delegate codex` — or per-run `/flow-next:work fn-12 delegate:codex`. Host keeps gating/git/review; `codex exec` writes code |
| **Orchestrator → reader** | Token-hungry, low-judgment reads (codebase analysis, doc sweeps) run on fast models that report summaries back — the orchestrator never holds the raw tokens | Already the default: planning scouts and prime scanners run on the fast tiers and return digests. Add `/flow-next:map` or the rp-explorer skill for token-efficient exploration |
| **Cross-family reviewer** | The model that writes is never the model that reviews — uncorrelated blind spots | `review.backend codex` / `cursor:composer-2.5` / `copilot:...` — per-task `review:` pins exceptions |
| **Effort discipline** | Run the orchestrator at high, not max — top effort tiers are token furnaces with flat-or-worse output on routine work | Session effort is yours; `work.delegateEffort` floors the delegate (`medium` default, per-batch risk escalation raises it) |
| **Token-hungry offload** | Computer use, live-app verification, bulk analysis go to other models/agents; results come back as evidence | `/flow-next:qa` drives the app in its own context and files P0/P1/P2 findings; workers run fresh-context and return receipts |

## Durable routing — a model table in CLAUDE.md

The emergent pattern (mid-2026): a standing "which model for what" section in your agent instructions — a ranking of the models you can reach plus routing rules. This is **prompted orchestration made durable**: the table is interpreted by intelligence, not parsed by a config loader. The host reads it every session and applies it *with judgment* when it dispatches subagents, picks reviewers, or decides to delegate — which is exactly why the rules grant standing permission to escalate.

flow-next ships this as a canonical scaffold — [`../skills/flow-next-setup/templates/model-routing-snippet.md`](../skills/flow-next-setup/templates/model-routing-snippet.md): a scores table (cost / intelligence / taste) over the session model, `gpt-5.6` (sol/terra), `composer-2.5`, and a fast Claude tier, plus how-to-apply rules and the exact flow-next surface each route drives (worker/`delegate:codex`, review backends, scouts, the thin-wrapper). `/flow-next:setup` offers to write it into your `CLAUDE.md`/`AGENTS.md` live, annotated for the CLIs you actually have installed. The shape, illustrated:

```markdown
| model                    | cost | intelligence | taste |
|--------------------------|------|--------------|-------|
| session model (frontier) | 2    | 10           | 9     |
| gpt-5.6-sol              | 8    | 9            | 6     |
| composer-2.5             | 9    | 6            | 6     |

- Defaults, not limits — escalate to a smarter model when output misses the bar.
- Delegated implementation → gpt-5.6-sol (delegate:codex, real work — never a cheaper tier); cheap bulk reads → gpt-5.6-terra; reviews cross-family; user-facing needs taste ≥ 7.
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
  Delegation is on (work.delegate=codex): mechanical tasks go to gpt-5.5,
  UI tasks stay on the session model, reviews come from codex.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK,
  or on any NEEDS_HUMAN.
```

Loop internals: [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md), [`ralph.md`](ralph.md) for the hardened harness.

## In your repo

This page lives in the plugin's doc tree — *outside* the repo you're working in. At use time the host agent reads two files that ship into your project, so the steering recipes are put where agents already look:

- **`.flow/usage.md`** carries an `## Orchestration & model steering` section (installed in every project, read every session): the headless `codex exec` / `cursor-agent` / `claude -p` bridge commands and the flow-next shortcuts (`delegate:codex`, `review.backend`, per-task `review:`, prompted-orchestration examples). The bridges run in **every direction** — `claude -p` lets a Codex or Cursor host conduct Claude the same way; any harness that can run Bash can be the conductor.
- **`CLAUDE.md` / `AGENTS.md`** can hold the durable model-routing table above: `/flow-next:setup` offers, as an optional ceremony step, to scaffold it live — annotated for the CLIs you actually have installed, shown in full before writing, yours to edit after. Marker-fenced so `/flow-next:uninstall` can remove it cleanly.

## What stays fixed

Steering is broad but not unbounded — these hold no matter what the routing table says:

- **Judgment stays with the host.** Delegated `codex exec` writes code; it never owns git, task state, review verdicts, or decisions.
- **Consent gates don't route away.** Delegation is off by default and one-time consented; sandbox blast radius is surfaced before first use; Ralph/headless requires consent pre-set.
- **Merge is human-gated** everywhere except the explicitly opted-in land loop (bounded license: `--squash --match-head-commit`, full gate tree first).
- **Verification is independent.** A delegated diff is never trusted on the delegate's own summary — the worker re-runs tests before `flowctl done`.
- **Escalation beats thrift.** Downgrade defaults are A/B-verified here; when you downgrade a role yourself, watch the first outputs and revert on the first quality miss.

## See also

- [`platforms.md`](platforms.md) — install matrix, Codex model mapping, cross-platform patterns.
- [`flowctl.md`](flowctl.md) — `review.backend` grammar, `work.delegate*` keys, `spec set-backend`.
- [`../skills/flow-next-work/references/codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md) — the delegation contract.
- [`ralph.md`](ralph.md) — autonomous-mode internals; delegation under Ralph.
- [`teams.md`](teams.md) — the handover objects that make cross-model hand-offs safe.

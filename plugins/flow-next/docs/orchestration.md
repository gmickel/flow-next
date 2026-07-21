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

The Codex mirror maps these to `gpt-5.5` / `gpt-5.4-mini` at sync time (`scripts/sync-codex.sh` `map_model`). Precedence at regen: env (`CODEX_MODEL_INTELLIGENT` / `CODEX_MODEL_FAST`) > role-map pins (`models.roles.scoutIntelligent.codex` / `scoutFast.codex` when present in the repo `.flow/config.json`) > those baselines. The worker keeps `inherit` on both platforms (your session model rules); an OPT-IN sync-time pin (`CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER`, recommended `gpt-5.6-terra` @ `medium`) lets Codex-host work threads ride the efficient tier. Details: [`platforms.md`](platforms.md).

### Role map: the one place pins rot (fn-115)

Hardcoded model pins used to scatter across the registry, triage defaults, `work.delegateModel`, and sync-codex scout constants. They all rot as providers ship tiers. The **role map** is the single config surface that is allowed to hold those pins:

```bash
flowctl config set models.roles.fastJudge.codex gpt-5.6-luna
flowctl config set models.roles.review.codex gpt-5.6-sol:medium
flowctl config set models.roles.delegate.codex gpt-5.6-terra
flowctl config set models.roles.scoutFast.codex gpt-5.6-luna
flowctl config set models.roles.scoutIntelligent.codex gpt-5.5
flowctl config set models.verifiedAt 2026-07-21
```

Roles name **jobs** (`fastJudge` / `review` / `delegate` / `scoutFast` / `scoutIntelligent`), not call sites. Resolution order extends the existing review precedence: explicit CLI / per-task pin > env > role map > registry baseline. Registry ladders stay as availability fallbacks (they heal pin-too-new); the role map heals pin-too-old.

**Refresh path is the setup ceremony**, not Python judgment. `/flow-next:setup` probes installed CLIs, the host agent judges which tiers fit each role, proposes Accept / Stamp-only / Skip, and writes accepted pins + `models.verifiedAt`. When `verifiedAt` is older than ~90 days, `flowctl status` prints one non-blocking line. Skills resolve pins with:

```bash
flowctl models resolve <role> [--backend codex] [--json]
```

Do not use `config get work.delegateModel` for the effective delegate model: the merged default bypasses the role map. Use `models resolve delegate`.

**Known Codex limitation (Jul 2026):** on GPT-5.6 Sol / Multi-Agent V2 builds, per-spawn model steering is unreliable end to end - `spawn_agent` stripped `model`/`reasoning_effort`/`agent_type` from its schema (openai/codex#31814, partially restored by #32749; `agent_type` still missing per #32782), explicit overrides are silently dropped when the agent carries a role layer (#33268), and role-profile application is not verifiable (#33314). Until those settle, the ROBUST way to steer a different model from a Codex host is the **same-family self-bridge**: `codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium "<self-contained prompt>"` - a fresh process taking `-m` on the command line, immune to the spawn_agent path entirely. Caveats: the child needs process-spawn + network inside the parent sandbox, and keep the child prompt flat (a child that spawns MAv2 subagents of its own can return undecodable results, #33267).

### Review backends — cross-model review

The review subsystem is the most routable surface. Spec grammar `backend[:model[:effort]]`, registry `rp | codex | copilot | cursor | none`. The three CLI review backends (`codex` / `copilot` / `cursor`) are `BACKEND_REGISTRY` entries driving one shared `cmd_backend_review` pipeline (fn-112); genuine variance is hooks, not cloned commands.

```bash
flowctl config set review.backend codex                    # project default
flowctl config set review.backend cursor:composer-2.5     # cursor folds effort into the model name
flowctl config set review.backend codex:gpt-5.4:xhigh     # explicit model + effort
```

Precedence (highest wins): per-task `review:` / per-spec `default_review` → `FLOW_REVIEW_BACKEND` → `.flow/config.json` `review.backend` → backend-specific env → registry default. A single task can pin a different reviewer than the project default and the override routes end-to-end. The `cursor` backend unlocks reviewer models the others can't reach in one place (`gpt-5.6-sol-high` at 1M context — the default, `gpt-5.6-terra`/`-luna`, `grok-4.5-high` (fast cross-family pass), `composer-2.5`, the `gpt-5.3-codex` family, `claude-opus-4-8-thinking-high`) on your existing Cursor subscription. Full grammar + registry: [`flowctl.md`](flowctl.md#review-backend).

**Rule of thumb: the model that writes is never the model that reviews.** Route the reviewer to a different family than your session model and blind spots stop being correlated.

**Cursor backend — ambient-injection caveat + persona override (fn-90).** `cursor-agent` has **no system-prompt mechanism**: the flow-next reviewer rubric travels as a plain user prompt *on top of* Cursor's own built-in persona (which carries its OWN review rubric and an end-to-end-thoroughness bias), and `cursor-agent` auto-attaches the workspace `AGENTS.md` / `CLAUDE.md`, skill catalogs, and MCP instruction blocks into the reviewer's context. That ambient guidance dilutes the in-scope anchor and biases the reviewer toward always-produce-findings — a real contributor to review-loop non-convergence (it *amplifies*, it is not the root cause). There is no CLI knob to suppress the auto-attach, so flow-next prepends an explicit **persona-override preamble** on every cursor review path: it declares that any ambient rubric/persona/severity-ordering from the environment is *superseded* and the ONLY rubric + verdict contract is the flow-next one that follows. This is documented, not configurable — nothing to set; it rides automatically on `review.backend cursor:*`. (The convergence ratchet + deterministic cap that actually *fix* the runaway apply to all backends — see [`flowctl.md`](flowctl.md#codex-impl-review).)

### Implementation delegation — `work` → `codex exec`

Opt-in offload of the token-heavy part (writing code) to a second CLI while the host keeps all judgment:

```bash
flowctl config set work.delegate codex            # activation predicate is exactly the string "codex"
flowctl config set work.delegateModel gpt-5.6-terra   # default (codex CLI >= 0.144) - passed as -m on the delegated codex exec
flowctl config set work.delegateEffort medium     # none|low|medium|high|xhigh floor - passed as -c model_reasoning_effort=
```

Or per-invocation: `/flow-next:work fn-12 delegate:codex`. The raw `codex exec` bridge is the interactive route; `delegate:codex` is the same bridge with deterministic rails for unattended loops. The prompt is a fixed path-handoff template - the task and spec files ARE the brief, never restated. The host retains gating, classification, git ownership, review, and commit; `codex exec` writes code and is forbidden from git and decisions. OFF by default, one-time consent-gated, circuit-breakered, with an independent verification backstop (the worker runs tests on the delegated diff even with `REVIEW_MODE=none`). Full contract: [`codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md).

The `gpt-5.6-terra` / `medium` defaults are eval-motivated, not arbitrary: a controlled pipeline eval (2026-07-14, hidden 39-check oracle suite, n=3 reps) had terra-medium match `gpt-5.6-sol` on correctness at roughly two-thirds the wall-clock on frontier-authored specs, with effort above `medium` pure overhead. One task, so motivation rather than guarantee - escalate `work.delegateModel` to `gpt-5.6-sol` when a task looks gnarly. Upgraders note: `flowctl init` persists defaults into `.flow/config.json` and raw values win, so installs initialized under an older default keep it until you run the `config set` above yourself.

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
| **Effort discipline** | Run the orchestrator at high, not max — top effort tiers are token furnaces with flat-or-worse output on routine work | Session effort is yours; `work.delegateEffort` floors the delegate (`medium` default, per-run risk escalation raises it) |
| **Token-hungry offload** | Computer use, live-app verification, bulk analysis go to other models/agents; results come back as evidence | `/flow-next:qa` drives the app in its own context and files P0/P1/P2 findings; workers run fresh-context and return receipts |

## A proven default pipeline

One controlled pipeline eval (2026-07-14: a hidden 39-check oracle suite for the work stage, a planted-bug review eval at n=3 reps per arm with matched reasoning efforts, dual cross-family blind judges for plans) produced a concrete default routing. It is one task's worth of evidence - motivation, not a guarantee - but it is the shape this repo now runs.

The roles are **model-per-role, not host-relative**: the bridges run in both directions (`codex exec` reaches GPT from a Claude host, `claude -p` reaches Claude from a Codex host), so the recommended model for each role is the same everywhere - only the *reach mechanism* differs by host.

| Role | Model | Why | Reach from a Claude Code host | Reach from a Codex host |
|------|-------|-----|-------------------------------|-------------------------|
| Plan (spec authoring: capture / interview / plan / plan-review critique) | Session frontier model | Two cross-family blind judges ranked frontier plans clearly ahead; raising effort on a weaker planner did not close the gap | Session-native | Session-native * |
| Plan-review | Cross-family frontier | Uncorrelated blind spots on the highest-leverage artifact | `--review=codex` / `review.backend codex` | `review.backend` to a non-GPT family (e.g. `cursor:...`) |
| Work (implementation) | `gpt-5.6-terra` @ `medium` | Matched `gpt-5.6-sol` on hidden-suite correctness at ~2/3 wall-clock on frontier-authored specs; effort above medium was pure overhead | `delegate:codex` (the `work.delegateModel` / `work.delegateEffort` defaults) | `codex exec -m gpt-5.6-terra` self-bridge (robust today); session model natively; opt-in sync-time pin `CODEX_MODEL_WORKER=gpt-5.6-terra` once MAv2 profile application is trustworthy |
| Impl-review, first pass | Cross-family from the writer - `gpt-5.6-sol` @ `high` when the writer is Claude-family | 12/12 recall on planted bugs, 0 false positives, fastest reviewer in the fleet (103s mean) | `review.backend codex` (pin `codex:gpt-5.6-sol:high`) - the session writes, sol reviews; no codex CLI? `cursor:gpt-5.6-sol-high` reaches sol through cursor | The worker writes GPT (terra), so sol would be SAME-family: route the first pass to a non-GPT reviewer instead - packaged rungs `review.backend copilot:claude-opus-4.5` / `cursor:claude-opus-4-8-thinking-high` (cursor also carries `claude-fable-5-thinking-high` — NO ZDR — and, for the reverse direction, `gpt-5.6-sol-high`), or Claude Code ad hoc via the `claude -p` reverse bridge (no packaged rung; prefer opus/sonnet targets - fable via `claude -p` can hit CLI credit limits) |
| Impl-review, final gate | Session frontier model | Only the frontier tier volunteered correct severity tiering and blast-radius judgment unprompted | Session-native (the host interprets the verdict; escalate disagreements to it) | Session-native |

\* Spec authoring is **session-native by design** — capture, interview, and plan are inline skills, so the session model is who writes and refines every spec - there is no packaged cross-family plan rung. Ad-hoc bridging works (`claude -p` can author a plan from a Codex host) but frontier-Claude via `claude -p` can hit CLI credit limits on plan-sized prompts (observed 2026-07-14); plan on whatever frontier model your session runs.

Notes that keep the table honest:

- **Single subscription? The table still reads correctly.** Most orgs run ONE harness subscription. Every row degrades to "the session model" and the pipeline works exactly as shipped - multi-model routing is optional garnish, never a prerequisite.
- **`gpt-5.6-luna` @ `xhigh`** is the equal-recall alternative for the first-pass reviewer (12/12) at ~2.5x the time; luna-medium is the budget delegate alternative (same hidden-suite correctness, tightest code, more tool-loop round-trips).
- **`grok-4.5` is a classic-bug quick pass ONLY - never the gate.** It missed the eval's subtle latent bug in all 3 runs. Fine as a cheap extra pass; a ship decision must not rest on it.
- Build-tier models are excluded from review roles entirely (in the same eval one missed a planted bug, another returned a false all-clear).
- **"Cross-family" is measured from the WRITER, not the host.** sol-high's 12/12 was earned reviewing Claude-family-written code; when your writer is GPT (e.g. the Codex mirror's terra-pinned worker), a GPT reviewer re-correlates the blind spots - pick the reviewer from whichever family did NOT write the diff.

### The wrapper pattern - self-healing bridges for unattended loops

Raw bridge calls have a silent-failure class: outside a trusted git directory, `codex exec` refuses in about a second with the error only in its log, and `cursor-agent` blocks on an interactive workspace-trust prompt, then exits "successfully" with empty output. An interactive host sees the stderr and just fixes it; an **autonomous loop dies silently**. The pattern that closed this in the eval: wrap the bridge in a thin fast-tier subagent (sonnet-class) instead of calling it raw. The wrapper composes the self-contained prompt, runs the bridge, verifies output is non-empty/parseable, repairs the environment if not, and retries once. Output quality was identical to raw calls.

Two rules are load-bearing:

- **The wrapper MUST run the bridge in the foreground** - one blocking Bash call. A backgrounded bridge loses the completion signal and the wrapper idles forever on a finished (or silently dead) process.
- **The self-heal license covers environment and flags only, never judgment.** In scope: git trust (`--skip-git-repo-check`, `git init` in a scratch dir), sandbox flags, stale model ids, empty-output retry. Out of scope: rewriting the task prompt, interpreting review verdicts, or switching models on quality grounds - judgment stays with the host.

This is a documented pattern, not a shipped agent type - the bridge recipes live in `.flow/usage.md` § Orchestration & model steering. Interactive sessions don't need it.

### Raw-bridge review prompts - demand severity tiers

Applies to **ad-hoc bridge reviews only** - a hand-rolled `codex exec` review whose output a human reads directly (the usage.md recipes). When you write one, put two things in the prompt:

- **P0-P3 severity tiers plus spec-grounded verdicts**, so an edge-case finding does not flip a ship gate. Reviewers reliably flag spec-gray edges as bugs (in the eval, behavior explicitly licensed by a plan amendment was reported as a defect by every reviewer) - severity tiers and "cite the spec line" are what keep those findings informative instead of gate-flipping.
- Optionally **a minimal suggested fix and blast radius per finding** when no fix loop follows the review. Control runs showed this artifact is prompt-shaped: models produce it when the prompt demands it and omit it when not asked.

The **packaged** `/flow-next:impl-review` prompt is deliberately NOT changed to this shape: its find-vs-fix split (the reviewer returns findings; the internal fix loop investigates and fixes, with validator and iteration caps) is by design, and its rubric already carries confidence anchors and introduced-vs-pre-existing classification. Deep-pass/validator merge math is autonomous-only (fn-113.4): under `FLOW_RALPH` / `REVIEW_RECEIPT_PATH` / `FLOW_AUTONOMOUS` flowctl mutates the receipt; interactive surfaces raw findings and the host judges.

## Durable routing — a model table in CLAUDE.md

The emergent pattern (mid-2026): a standing "which model for what" section in your agent instructions — a ranking of the models you can reach plus routing rules. This is **prompted orchestration made durable**: the table is interpreted by intelligence, not parsed by a config loader. The host reads it every session and applies it *with judgment* when it dispatches subagents, picks reviewers, or decides to delegate — which is exactly why the rules grant standing permission to escalate.

flow-next ships this as a canonical scaffold — [`../skills/flow-next-setup/templates/model-routing-snippet.md`](../skills/flow-next-setup/templates/model-routing-snippet.md): a scores table (cost / speed / intelligence / taste) over the session model, `gpt-5.6` (sol/terra), `grok-4.5`, `composer-2.5`, and a fast Claude tier, plus how-to-apply rules and the exact flow-next surface each route drives (worker/`delegate:codex`, review backends, scouts, the thin-wrapper). `/flow-next:setup` offers to write it into your `CLAUDE.md`/`AGENTS.md` live, annotated for the CLIs you actually have installed. The shape, illustrated (cost = subscription-quota lightness, not list $/token; speed = at default reasoning effort):

```markdown
| model                    | cost | speed | intelligence | taste |
|--------------------------|------|-------|--------------|-------|
| session model (frontier) | 2    | 2     | 10           | 9     |
| gpt-5.6-sol              | 8    | 5     | 9            | 6     |
| grok-4.5                 | 9    | 9     | 7            | 5     |
| composer-2.5             | 9    | 10    | 6            | 6     |

- Defaults, not limits — escalate to a smarter model when output misses the bar.
- Delegated implementation → gpt-5.6-terra @ medium (delegate:codex; escalate to gpt-5.6-sol when a task looks gnarly); fast/cheap first-draft implementation → grok-4.5 (`grok -p`); cheap bulk reads → gpt-5.6-terra; reviews cross-family; user-facing needs taste ≥ 7.
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
  Delegation is on (work.delegate=codex): implementation tasks go to gpt-5.6-terra,
  UI tasks stay on the session model, reviews come from codex.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK,
  or on any NEEDS_HUMAN.
```

Loop internals: [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md), [`ralph.md`](ralph.md) for the hardened harness.

## In your repo

This page lives in the plugin's doc tree — *outside* the repo you're working in. At use time the host agent reads two files that ship into your project, so the steering recipes are put where agents already look:

- **`.flow/usage.md`** carries an `## Orchestration & model steering` section (installed in every project; read on demand - the always-loaded CLAUDE.md/AGENTS.md block points agents at it): the headless `codex exec` / `cursor-agent` / `claude -p` bridge commands and the flow-next shortcuts (`delegate:codex`, `review.backend`, per-task `review:`, prompted-orchestration examples). The bridges run in **every direction** — `claude -p` lets a Codex or Cursor host conduct Claude the same way; any harness that can run Bash can be the conductor.
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

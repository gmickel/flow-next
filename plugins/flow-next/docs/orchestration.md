# Orchestration & model routing

flow-next is an orchestration layer, not a single-agent workflow. The host agent (Claude Code / Codex / Droid) conducts: it fans work out to tiered subagents, routes reviews to a *different* model family than the writer, optionally delegates implementation to a second CLI agent, and runs autonomous build/ship loops. Which model does what is a routing decision — and every routing decision in flow-next is either a config surface or a prompt away.

The pattern this page serves: use your smartest model to orchestrate and judge, route mechanical or token-hungry work to faster/cheaper models, and pick reviewers from a different family than the writer. flow-next was built in this shape — this page maps the dials.

**None of this is required.** The skills and subagents ship pre-tuned to work well out of the box for everyone — model tiers A/B-verified before every downgrade, review defaults sensible, the pipeline complete with zero routing config. Steering is a capability, not a prerequisite: reach for the dials below when your model mix, subscriptions, or taste differ from the defaults, and ignore this page entirely until they do.

## The steering principle

**Skills are prompts executed by the host agent, not compiled code.** Nothing in a skill is hidden behind a binary — so steering doesn't need a fork or a flag the skill authors anticipated. Three tiers:

| Tier | Mechanism | Scope | Example |
|------|-----------|-------|---------|
| **One-off** | Say it in the invocation | this run | `/flow-next:plan fn-12 — keep the research on the auth migration; skip the web scouts` |
| **Durable** | Standing rule in `CLAUDE.md` / `AGENTS.md` | every session in the repo | "When running `/flow-next:work` on mechanical tasks, use `delegate:codex`" |
| **Config** | `.flow/config.json` keys + per-spec/per-task fields | the built-in routing surfaces | `flowctl config set review.backend cursor:composer-2.5` |

Extra instruction the skill doesn't parse isn't an error — the host reads it as intent. Focus hints ("push hard on failure modes"), scope restrictions, model preferences, and reviewer choices all route this way. The durable tier is just the one-off tier written down: the host reads your agent instructions every session, and flow-next skills inherit them automatically because the host is the one executing them.

## Built-in routing surfaces

### The host model — the conductor

You pick it in your harness (e.g. `/model`). The host owns everything that requires judgment: gating, task classification, git, review-verdict interpretation, user consent. Workers and resolvers ship with `model: inherit`, so the session model *is* the implementation model unless you delegate (below). Practical consequence: a frontier session model gives you a frontier planner *and* frontier workers; dropping the session model for a mechanical spec drops both.

### Subagent tiers

The bundled agents are pre-tiered by task shape (each A/B-verified before downgrade — see `agents/*.md` frontmatter):

| Tier | Agents | Why |
|------|--------|-----|
| fast (`haiku`) | prime's pillar scanners (build/env/security/testing/tooling/workflow/observability/memory-scout) | mechanical scan-and-report |
| judgment (`sonnet`) | planning scouts (repo/context/spec/docs/github/practice), flow-gap-analyst, plan-sync | read-and-judge, bounded scope |
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

Precedence (highest wins): per-task `review:` / per-spec `default_review` → `FLOW_REVIEW_BACKEND` → `.flow/config.json` `review.backend` → backend-specific env → registry default. A single task can pin a different reviewer than the project default and the override routes end-to-end. The `cursor` backend unlocks reviewer models the others can't reach in one place (`gpt-5.5-high` at 1M context, `composer-2.5`, the `gpt-5.3-codex` family, `claude-opus-4-8-thinking-high`) on your existing Cursor subscription. Full grammar + registry: [`flowctl.md`](flowctl.md#review-backend).

**Rule of thumb: the model that writes is never the model that reviews.** Route the reviewer to a different family than your session model and blind spots stop being correlated.

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

## One-off steering — just ask

Everything above has a prompt-level equivalent, and plenty of steering has no config key at all:

```text
/flow-next:plan fn-12 --depth=deep — focus the research on the migration path; I care about rollback
/flow-next:interview fn-12 — push hard on failure modes and operational edges, skip UI polish
/flow-next:work fn-12 delegate:codex
/flow-next:impl-review fn-12 --review=cursor:composer-2.5
/flow-next:pilot --review=codex --research=grep --depth=short
```

## Durable routing — a model table in CLAUDE.md

The emergent pattern (mid-2026): a standing section in your agent instructions that ranks the models you can reach on cost / capability / taste, plus routing rules. flow-next needs no integration for this — the host reads it every session and applies it when it dispatches subagents, picks reviewers, or decides to delegate. Example shape:

```markdown
## Model routing

| role | route to | why |
|------|----------|-----|
| Orchestrate, plan, judge reviews | session model (frontier) | judgment work — never downgrade |
| Implement well-specced tasks | codex exec / gpt-5.5 (`delegate:codex`) | steerable, covered by my existing sub |
| Review plans + implementations | `review.backend cursor:composer-2.5` | different family than the writer |
| Bulk reads, codebase analysis | fast model via a scout/subagent | token-hungry, low-judgment |

Rules:
- When running /flow-next:work on tasks classified mechanical, use delegate:codex.
- Judge the output, not the price tag: if a cheaper model misses the bar, redo with a smarter one without asking.
- Escalate NEEDS_WORK disagreements between reviewer and worker to the session model.
```

Role labels are durable; model IDs are volatile. Write the table in terms of roles and swap the IDs as the frontier moves.

## Chaining the loops

Pilot and land end every tick with machine-readable verdict lines precisely so a host driver can compose them. Pilot never merges and never invokes land (consent boundary); the *driver* routes between them:

```text
/loop 30m — one tick: run /flow-next:pilot --review=codex.
  If it prints PILOT_VERDICT=DEFERRED_TO_LAND, run /flow-next:land in the same tick.
  Stop when pilot prints NO_WORK and land prints LAND_VERDICT=NO_WORK, or on any NEEDS_HUMAN.
```

`DEFERRED_TO_LAND` exists exactly for this hand-off — every remaining spec has an open PR that land, not pilot, owns. Compose model routing into the same driver ("reviews on codex, delegation on, workers on the session model") and you have a multi-model spec-to-merged-PR pipeline in one prompt. Loop internals: [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md), [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md), [`ralph.md`](ralph.md) for the hardened harness.

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

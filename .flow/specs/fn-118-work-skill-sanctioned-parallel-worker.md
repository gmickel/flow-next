# fn-118 Prompt-guided parallel work from the task DAG

## Goal & Context
<!-- scope: business -->

Flow-Next already records task dependencies and expected files, but `/flow-next:plan` does not clearly show which tasks form parallel execution waves and `/flow-next:work` still describes a strictly sequential task loop. The public documentation already tells users that disjoint tasks can run in parallel.

Make that behavior native to the skills without adding a scheduler. Planning should prefer meaningful task boundaries that expose safe parallelism and show the resulting waves. Work should inspect the ready frontier, parallelize when the host can do so safely, and choose an appropriate isolation/integration approach from the host's available capabilities. When safety or capacity is uncertain, it should continue sequentially.

## Architecture & Data Models
<!-- scope: technical -->

No new runtime, schema, manifest, CLI option, or deterministic scheduler.

The existing task DAG remains the source of truth:

- task `depends_on` edges define ordering;
- `**Files:**` and task context help the agent judge whether ready tasks are meaningfully disjoint;
- `flowctl ready --spec <id> --json` returns the current ready frontier;
- the host agent chooses whether to run some or all of that frontier concurrently;
- the host chooses native isolation, linked worktrees, another safe workspace mechanism, or sequential fallback;
- existing worker completion, review, failure recovery, tracker, and plan-sync contracts remain authoritative.

The planner should not split cohesive work merely to manufacture parallelism. It should avoid unnecessary dependencies, prefer disjoint ownership when task quality is unchanged, and print compact execution waves after validation so users can see the intended DAG.

### Minimal parallel-worker lifecycle

Parallel workers reuse the existing host-deferred handover shape rather than completing Flow state inside isolated branches:

1. The conductor selects a safe subset of the ready frontier, claims each selected task, chooses an isolated workspace per worker, and reports the selected task IDs plus isolation choice.
2. Each worker receives one task and an explicit parallel-wave mode. It implements, tests, and commits in its assigned workspace, writes summary/evidence to task-unique paths, and returns those paths plus its commits/workspace. It does not call `flowctl done`, project tracker state, invoke plan-sync, or integrate itself.
3. The conductor joins the whole dispatched wave, reports each outcome, and uses the host's available integration mechanism to bring successful worker commits onto the target branch.
4. On the integrated target, the conductor applies the existing per-task verification/review/completion/tracker contract and calls `flowctl done`. Partial failures follow the existing ground-truth recovery rules; no batch state is added.
5. Downstream plan-sync runs after the wave is joined and resolved, never while peer workers are still active. The next ready frontier is then recomputed.

This is skill guidance, not a fixed Git topology. The host may use native worktree isolation, Flow's worktree kit, or another safe mechanism. If it cannot safely isolate and integrate a wave, it explains the fallback and runs sequentially.

## Quick commands

```bash
python3 -m unittest plugins.flow-next.tests.test_parallel_work_prose -v
./scripts/sync-codex.sh
python3 scripts/run_tests_parallel.py
lychee --offline --no-progress --root-dir "$(pwd)" --exclude-path plugins/flow-next/codex --exclude-path .flow --exclude-path node_modules --exclude-path flow-next-tui/node_modules README.md CONTRIBUTING.md SECURITY.md GLOSSARY.md STRATEGY.md agent_docs plugins/flow-next/README.md plugins/flow-next/docs plugins/flow-next/skills
cd /Users/gordon/work/flow-next.dev && pnpm build
```

Mirror idempotency is checked by snapshotting the generated Codex tree after the first sync, running sync again, and asserting the second run changes nothing. It is not inferred from a globally clean worktree.

## API Contracts
<!-- scope: technical -->

No new public flags. Natural-language and ordinary spec execution use the same behavior:

- `/flow-next:plan` reports dependency-ordered execution waves and labels tasks in the same wave as parallel candidates.
- `/flow-next:work <spec-id>` prefers a concurrent wave when multiple ready tasks are safe to isolate.
- An explicit user request to parallelize strengthens that preference but does not override safety.
- A single-task invocation remains single-task.
- Missing/ambiguous ownership, shared resources, unavailable isolation, insufficient host capacity, or integration uncertainty cause sequential execution with a short explanation.

## Edge Cases & Constraints
<!-- scope: technical -->

- Dependency correctness and cohesive task sizing outrank parallelism.
- Disjoint file lists are evidence, not proof; the host must consider shared lockfiles, generated outputs, migrations, fixtures, services, and other non-file coupling.
- Concurrent workers must not mutate the same checkout or share generic evidence paths.
- Claim selected tasks before dispatch so another run cannot take the same work.
- Join the current wave before selecting the next frontier or running downstream plan-sync.
- Compact progress must name the ready/selected task IDs, isolation choice, dispatch count, worker outcomes, join completion, and any sequential fallback reason.
- Parallel workers use task-unique handover files and defer `flowctl done` plus tracker/plan-sync work to the conductor after integration.
- Partial success uses the existing per-task ground-truth recovery contract; no new batch state is introduced.
- Canonical Claude-native prose must regenerate to the Codex mirror and remain portable for Cursor, Droid, and Grok.
- Changes land under `## Unreleased`; no version bump.

## Acceptance Criteria
<!-- scope: both -->

- **R13:** The plan skill prefers meaningful file-disjoint task boundaries when this does not harm cohesion, avoids unnecessary dependency edges, and reports the validated task DAG as execution waves with same-wave parallel candidates visible.
- **R14:** The work skill inspects the full ready frontier and prefers concurrent dispatch of a safe subset, while retaining host judgment over eligibility, worker count, isolation, integration, and sequential fallback.
- **R15:** Parallel-wave guidance uses a minimal host-deferred worker handover: isolated workers commit and return task-unique summary/evidence without completing Flow state; the conductor joins, integrates, then applies existing per-task review/completion/tracker contracts, and downstream plan-sync waits until the wave is resolved.
- **R16:** Focused prose regressions cover canonical and generated Codex plan/work/worker contracts, including compact progress/fallback reporting; repository and flow-next.dev documentation describe agent-chosen parallelism accurately without claiming that atomic task claims make shared-checkout work safe.

## Boundaries
<!-- scope: business -->

Out of scope:

- a `--parallel` CLI or configuration surface;
- fixed worker counts or deterministic eligibility rules;
- path/glob overlap parsers;
- batch manifests or recovery state machines;
- a new public worker handover schema;
- a deterministic cherry-pick scheduler or cleanup command;
- changing `flowctl ready`, task storage, or claim locking;
- guaranteeing parallel execution on hosts without safe isolation/capacity.

## Decision Context
<!-- scope: both -->

The host agent already has the judgment and platform tools needed to choose a safe arrangement. Encoding that judgment as Python or a detailed state machine would duplicate host capability, hard-code one Git topology, and make a prompt-level behavior unnecessarily expensive to maintain.

The deterministic layer continues to own task dependencies, readiness, and atomic claims. The agentic layer owns task decomposition, concurrency judgment, isolation choice, handover/integration orchestration, and fallback.

## Investigation Targets

- `plugins/flow-next/skills/flow-next-plan/steps.md:57-64` — existing disjoint-file planning guidance.
- `plugins/flow-next/skills/flow-next-plan/steps.md:412-426` — task creation and dependencies.
- `plugins/flow-next/skills/flow-next-work/SKILL.md:203-207` — conductor/worker ownership.
- `plugins/flow-next/skills/flow-next-work/phases.md:181-210` — currently sequential ready-task loop.
- `plugins/flow-next/skills/flow-next-work/phases.md:381-437` — existing plan-sync and loop behavior.
- `plugins/flow-next/agents/worker.md:399-481` — host-deferred handover and generic evidence paths to reuse safely.
- `plugins/flow-next/skills/flow-next-worktree-kit/SKILL.md` — reusable linked-worktree option.
- `scripts/sync-codex.sh` — generated mirror contract.

## Execution Waves

- **Wave 1 (parallel):** fn-118-work-skill-sanctioned-parallel-worker.1 and fn-118-work-skill-sanctioned-parallel-worker.2.

## Task Breakdown

1. **Planner/work/worker prompt contracts** — expose execution waves, prefer safe parallel ready-frontier dispatch, reuse host-deferred task-unique handovers, preserve agent-owned isolation choice and sequential fallback, add focused prose regressions, regenerate Codex.
2. **Documentation alignment** — correct repository and flow-next.dev concurrency guidance, including the distinction between task claims and filesystem/Git isolation.

## Early Proof Point

Task fn-118-work-skill-sanctioned-parallel-worker.1 is the technical proof that the behavior fits the existing planner/work/worker contracts without deterministic machinery. The documentation task may proceed in parallel against this reviewed contract; if implementation reveals a contradiction, both tasks must converge on the implemented behavior before completion.

## Requirement Coverage

| Req | Description | Task(s) | Gap justification |
|---|---|---|---|
| R13 | Planner exposes and biases toward useful parallel waves | fn-118-work-skill-sanctioned-parallel-worker.1 | — |
| R14 | Work prefers safe host-chosen parallel dispatch | fn-118-work-skill-sanctioned-parallel-worker.1 | — |
| R15 | Parallel worker defers shared lifecycle to conductor | fn-118-work-skill-sanctioned-parallel-worker.1 | — |
| R16 | Regression and documentation truth surfaces align | fn-118-work-skill-sanctioned-parallel-worker.1, fn-118-work-skill-sanctioned-parallel-worker.2 | — |

# guidance-eval — how much doc does an agent need to use flow-next correctly?

A clean-room harness that measures whether the **always-loaded** flow-next
instruction block (the "## Flow-Next" block `/flow-next:setup` writes into
`CLAUDE.md` / `AGENTS.md`) is sufficient for a fresh agent to track a piece of
work correctly — spec → task → start → implement → `done` with valid evidence —
with **no other flow-next docs present**.

It exists because an [18-run eval on 2026-07-15](../../CHANGELOG.md) found the
one thing docs measurably buy is the **evidence-JSON schema**: the old
575-token block named `--evidence-json e.json` but never showed the shape, and
`flowctl done --help` names the flag but not the schema — so capable agents
reliably called `done` **without valid evidence**. A single inline example
closed the gap. This harness re-runs that measurement on demand so future block
edits can be re-verified on the weakest routed model before they ship.

**This is a maintainer dev tool.** It is committed and documented but **not
CI-wired**: it needs network, model access, and real wall-clock time, and its
grades are model-dependent. The mechanical proxy that *is* CI is the
token-budget tripwire test on the snippet template (see the fn-99 spec). Run
this harness by hand when the block content changes.

## Layout

```
guidance-eval/
  runner.sh              # scaffold + drive the scenario×arm×model×rep matrix, grade, summarize
  setup.sh               # scaffold ONE clean-room scratch repo for one cell
  grade.py               # deterministic grader for one scratch repo (prints one JSON line)
  arms/
    minimal-block.md     # ~110-token block, syntax-neutral, WITH inline evidence schema
                         # (full-block arm is pulled LIVE from the shipped template — see Arms)
  scenarios/
    slugify.txt          # (a) single-task: implement + test a slugify() helper
    multitask.txt        # (b) multi-task: 2 tasks, a dependency, and a reset lifecycle event
```

## Running it

Prerequisites: `claude` and `codex` CLIs on `PATH`, authenticated; `python3`;
`git`. Scratch repos are created **outside** this checkout (default under
`$TMPDIR`) — see Threat model.

```bash
cd agent_docs/guidance-eval

# Full R13 baseline matrix (scenarios × arms × models × reps):
./runner.sh

# Cheap smoke (one cell):
SCENARIOS=slugify ARMS=minimal MODELS=haiku REPS_DISCRIMINATING=1 ./runner.sh
```

Overridable env vars (defaults in parentheses):

| var | default | meaning |
|---|---|---|
| `SCENARIOS` | `slugify multitask` | which scenario prompts to run |
| `ARMS` | `minimal full` | guidance block variants |
| `MODELS` | `sonnet haiku terra-medium` | bridge models |
| `REPS_DISCRIMINATING` | `3` | reps for evidence-validity-discriminating cells (Claude family) |
| `REPS_DEFAULT` | `1` | reps for the rest |
| `TIMEOUT_SECS` | `900` | per-run wall-clock ceiling (kill-tree on expiry) |
| `MAX_CONCURRENCY` | `4` | concurrent cells |
| `RUN_ROOT` | `$TMPDIR/flow-guidance-eval-<pid>-<ts>` | scratch + artifact root (must be OUTSIDE any git repo) |

Outputs land under `RUN_ROOT`:

- `results/results.jsonl` — one grade object per cell (ledger source)
- `results/summary.md` — batch summary + a failed/incomplete list
- `<run_id>/agent.log` — retained bridge stdout+stderr per run
- `<run_id>/.flow/invocations.log` — the flowctl shim log per run

## Arms

- **minimal** — `arms/minimal-block.md`, a ~110-token block written to be
  syntax-neutral (no slash-command references) so it drops into both `CLAUDE.md`
  and `AGENTS.md` unchanged. Carries the flowctl-only + no-TodoWrite rules, the
  typical-flow one-liner, the inline evidence schema, and the re-anchor rule.
- **full** — the **current shipped** block, pulled **live** at scaffold time from
  `plugins/flow-next/skills/flow-next-setup/templates/{claude,agents}-md-snippet.md`
  (marker lines stripped; the `claude` twin for Claude models, the `agents` twin
  for Codex). It is derived live, not snapshotted, so the baseline always reflects
  the block a fresh repo actually gets — no drifting copy to maintain.

Both arms ship **no `.flow/usage.md`**: the harness isolates the always-loaded
block. `usage.md` is on-demand; agents reach it (and `--help`) themselves.

## Scenarios

- **slugify** (single-task) — implement `src/slugify.py` + tests, tracked
  start-to-finish. The original discriminating scenario.
- **multitask** — a single spec with two tasks where the second **declares a
  dependency** on the first, plus a forced **reset lifecycle event**: after the
  first task is `done`, a requirement change forces a `task reset` back to todo,
  a re-implement, and a re-`done`, before the dependent task finishes. Exercises
  the dependency + reset flows the single-task scenario never touched.

## Grading contract

`grade.py <scratch_dir>` reads only committed state — the scratch repo's flow
state (via the real `flowctl`, not the shim) and the shim's `invocations.log` —
and prints one JSON object. No network, no model, no judgement: the same repo
grades identically forever.

Dimensions (common):

| field | meaning |
|---|---|
| `spec_created` | a spec exists |
| `n_tasks` | tasks under the first spec |
| `any_task_done` / `all_tasks_done` | task completion |
| `evidence_ok` | **every** done task carries valid evidence (see below) |
| `md_todos` | forbidden `TODO*/TASKS*/PLAN*.md` at repo root (want empty) |
| `tests_green` | `python3 -m unittest discover -s tests` exits 0 |
| `committed` | commits beyond the scaffold commit |
| `flowctl_calls` / `flowctl_errors` | agent flowctl invocations / non-zero-rc ones |

**Evidence validity** (the sole correctness-critical contract): the evidence is
a dict with keys `commits`, `tests`, `prs`, each a **list of strings**, and at
least one commit recorded. This mirrors what `agents/worker.md` teaches and
`cmd_done` accepts. The historical failure mode is `done` with no/empty
evidence — this dimension is what the whole eval discriminates on.

Scenario-specific:

- **slugify** score `/7`: `spec_created`, `any_task_done`, `evidence_ok`,
  `tests_green`, no `md_todos`, `committed>0`, `src_present` (`src/slugify.py`).
- **multitask** score `/10`: `spec_created`, `n_tasks>=2`, `has_dependency`
  (a task declares `depends_on` on **another in-spec task** — a dangling/
  out-of-spec dep does not count), `lifecycle_event` (a **successful** `task reset`
  or `block` targeting an **in-spec task** in the shim log — a failed or
  wrong-target command does not count), `all_tasks_done`, `evidence_ok`,
  `tests_green`, no `md_todos`, `committed>0`, `src_present` (`src/envconf.py`).

`grade.py` also emits `passed` (every scored dimension satisfied). The runner
keeps `status` (did the run COMPLETE) and `passed` (did it score full marks)
distinct: a completed run that scores low — e.g. an evidence miss — is a valid
data point, not an incomplete run, and the batch summary reports both (a
completed-but-not-passed run is never hidden as a success).

## Clean-room + hardening contract (binding)

Prior eval rounds proved each of these matters; they are not optional.

- **`claude -p --bare`** — without `--bare`, the maintainer's `~/.claude` global
  `CLAUDE.md` and plugins leak into the scratch repo and confound the arm under
  test (observed round-1 contamination). Plus explicit
  `--permission-mode acceptEdits --allowedTools "Read,Bash,Edit,Write,Grep,Glob"`.
- **`codex exec --sandbox danger-full-access --skip-git-repo-check`** —
  `workspace-write` demonstrably **blocks `git commit`** in scratch dirs, which
  makes an agent `block` its own task and confounds grading (observed round-1).
- **Foreground bridge calls, per-run timeout + process-group termination** — each
  bridge runs in the foreground of its worker (rc captured), launched in its own
  **session/process group** (via `perl` `setsid`, since macOS has no `setsid(1)`),
  under a wall-clock deadline that signals the **whole group** (`kill -TERM/-KILL
  -<pgid>`) on expiry. Group signalling — not a pid-tree walk — catches
  descendants even after they are reparented when the bridge parent exits. A hung
  model never wedges the batch, and no unsandboxed Codex subprocess escapes.
- **Unique run ids; cwd + nested-git-root preflight** — every cell has a unique
  id; before every bridge call the harness asserts the scratch dir is its **own**
  git root (not nested inside a parent repo) and lives outside this checkout.
- **Retained artifacts + batch summary** — per-run `agent.log`, shim log, and
  grade JSON are kept; the batch ends with a failed/incomplete summary.

## Threat model / exposure

The Codex arm runs `--sandbox danger-full-access`: the agent executes arbitrary
shell **without OS sandboxing**. A container/VM requirement was deliberately
**declined** (fn-99 Decision Context) — this is a maintainer dev tool in
`agent_docs/`, the same trust level as the maintainer's daily `danger-full-access`
Codex usage, and `workspace-write` confounds the very thing being measured.

Mitigations the harness *does* enforce: scratch repos live **outside** this
checkout (`RUN_ROOT` default under `$TMPDIR`, with a hard nested-git-root guard
so an agent's `git` can never touch the flow-next tree), each cell is its own
throwaway git repo, and every bridge is timeout- and kill-tree-bounded.

**If you do not accept that exposure**, run the harness inside a container or VM
(mount the repo read-only, set `RUN_ROOT` to a tmpfs inside the sandbox), or drop
the Codex arm (`MODELS="sonnet haiku"`). The Claude arms run under
`--permission-mode acceptEdits` and are lower-exposure but still execute agent
shell.

## Results ledger

Optimization-log style; append a row per batch. Record model ids + date + the
scenario×arm×model×rep matrix. `evidence_ok` is the load-bearing column.

<!-- LEDGER:START -->

### Baseline — "post-block-diet, pre-usage-trim" (2026-07-16, fn-99…2)

Recorded AFTER the block diet (fn-99…1: `claude-md-snippet.md` / `agents-md-snippet.md`
now ~248 tok WITH the inline evidence schema) and BEFORE any `usage.md` trim
(fn-99…3/.4). This is the attribution anchor for the post-trim gate: a post-trim
regression is measured against these rows.

**R13 matrix:** scenarios {slugify, multitask} × arms {minimal, full} × models
{sonnet (`claude -p --bare`), gpt-5.6-terra @ medium (`codex exec`), haiku
(`claude -p --bare`)} × reps {3 on the evidence-validity-discriminating cells
(the Claude family, where the historical evidence-miss lived), 1 elsewhere}.

Tool ids: `codex-cli 0.144.1`, model `gpt-5.6-terra` `model_reasoning_effort=medium`;
`claude 2.1.210`, models `sonnet` / `haiku`. Grader: `grade.py` @ this commit.

| date | scenario | arm | model | reps | score | evidence_ok | tests_green | lifecycle | flowctl_calls | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-16 | slugify | full | gpt-5.6-terra med | 1 | 7/7 | ✅ | ✅ | — | 16 | clean |
| 2026-07-16 | slugify | minimal | gpt-5.6-terra med | 1 | 7/7 | ✅ | ✅ | — | 17 | clean (1 err: `validate` guess) |
| 2026-07-16 | multitask | full | gpt-5.6-terra med | 1 | 10/10 | ✅ | ✅ | reset | 41 | dep + reset exercised |
| 2026-07-16 | multitask | minimal | gpt-5.6-terra med | 1 | 10/10 | ✅ | ✅ | reset | 55 | dep + reset; 3 errs (`reset --help`, `dependency --help`, `set-spec --help`) — minimal→more --help exploration, matches "docs buy efficiency" |
| 2026-07-16 | slugify | full | sonnet | 3 | _pending_ | — | — | — | — | see env note below |
| 2026-07-16 | slugify | minimal | sonnet | 3 | _pending_ | — | — | — | — | see env note below |
| 2026-07-16 | slugify | full | haiku | 3 | _pending_ | — | — | — | — | see env note below |
| 2026-07-16 | slugify | minimal | haiku | 3 | _pending_ | — | — | — | — | see env note below |
| 2026-07-16 | multitask | * | sonnet | 3 | _pending_ | — | — | — | — | see env note below |
| 2026-07-16 | multitask | * | haiku | 3 | _pending_ | — | — | — | — | see env note below |

**Reading the codex rows:** post-diet, BOTH arms produce **valid evidence** on
both scenarios and both families of task graph — the dieted block's inline schema
holds, and the ~110-token minimal arm matches the ~248-token full arm on every
scored dimension (its only cost is efficiency: more `--help` exploration and a
`close`-command guess, exactly the "docs buy efficiency, not correctness"
finding). The multitask scenario confirms the dependency + `task reset` flows the
original single-task eval never exercised.

**Claude-family rows are pending an API-key environment (env constraint, not a
harness defect).** `--bare` (the binding clean-room method — it disables the
`~/.claude` global-CLAUDE.md leak that otherwise confounds the arm under test)
authenticates **strictly** via `ANTHROPIC_API_KEY` or `apiKeyHelper`, not OAuth /
keychain. The worker this baseline was recorded on has no `ANTHROPIC_API_KEY`, and
running non-`--bare` was verified to leak Gordon's global `CLAUDE.md` ("Gordon owns
this") into a `/tmp` scratch — which would poison the measurement. Complete these
rows from a shell with an API key:

```bash
cd agent_docs/guidance-eval
ANTHROPIC_API_KEY=… MODELS="sonnet haiku" ./runner.sh   # appends sonnet+haiku cells
```

The historical evidence-miss (the reason this eval exists) lived in the Claude
family on the block-WITHOUT-schema; both arms here now carry the schema, so the
expected result is valid evidence across the board — but the haiku floor must be
re-confirmed in an API-key environment before the fn-99…4 post-trim gate is
declared green.

<!-- LEDGER:END -->

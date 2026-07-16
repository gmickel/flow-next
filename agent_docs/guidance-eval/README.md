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
    usage-pretrim.md     # frozen pre-trim usage.md (5392 tok-equiv, pre-fn-99…3) for the
                         # usage-included trim gate (full-usage-pretrim arm)
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

The two block-only arms ship **no `.flow/usage.md`**: they isolate the
always-loaded block. Two further **usage-aware** arms exist for gating a
`usage.md` trim with usage.md actually present (a block-only matrix cannot see a
usage.md regression by construction):

- **full-usage** — the full block PLUS the **current shipped**
  `templates/usage.md` (post-trim), pulled live, installed at
  `.flow/usage.md` exactly where `/flow-next:setup` puts it.
- **full-usage-pretrim** — the full block PLUS the frozen pre-trim fixture
  `arms/usage-pretrim.md` (5392 tok-equiv, the template as of the commit before
  fn-99…3's trim). The comparison anchor: same block, only the usage.md differs.

Both usage-aware arms use the canonical (slash-syntax) template for both
families — the codex mirror's copy differs only in invocation-syntax tokens,
which none of the scenario flows exercise. Run them via
`ARMS="full-usage full-usage-pretrim" ./runner.sh`; the default `ARMS` stays
`minimal full` (block-only).

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

**Committed-state grading.** `committed>0` alone is gameable (an empty commit
plus uncommitted implementation). So the scored `src_committed` dimension requires
the scenario's source file to be tracked in `HEAD` (`git cat-file -e HEAD:<path>`)
**and** to match the worktree (`git diff --quiet HEAD -- <path>`) — the code the
tests run against is exactly the committed code. A whole-tree clean check is NOT
scored (the shim's `invocations.log`, `agent.log`, `.flow` state sidecars, and
`__pycache__` leave the tree dirty by construction); `worktree_clean` is emitted
as an informational field only.

`tests_green` requires the suite to exit 0 **and** at least one test to have
actually run (`unittest discover` exits 0 on zero discovered tests, so a
green-with-no-tests run must not pass). `tests_committed` requires the scenario's
test file to be committed + clean (so the tests that ran are the committed ones).

Scenario-specific:

- **slugify** score `/7`: `spec_created`, `any_task_done`, `evidence_ok`,
  `tests_green` (≥1 test ran), no `md_todos`, `src_committed` (`src/slugify.py` in
  HEAD and clean), `tests_committed` (`tests/test_slugify.py` in HEAD and clean).
- **multitask** score `/10`: `spec_created`, `n_tasks>=2`, `has_dependency`
  (a task declares `depends_on` on **another in-spec task** — a dangling/
  out-of-spec dep does not count), `lifecycle_ordered` (the prescribed workflow
  verified as an ordered subsequence in the shim log: **`done(prereq)` →
  `reset(prereq)` → `done(prereq)` → `done(dependent)`**, all rc==0 and in-spec —
  a failed, wrong-target, or out-of-order sequence does not count), `all_tasks_done`,
  `evidence_ok`, `tests_green` (≥1 test ran), no `md_todos`, `src_committed`
  (`src/envconf.py` in HEAD and clean), `tests_committed` (`tests/test_envconf.py`
  in HEAD and clean).

`grade.py` also emits `passed` (every scored dimension satisfied). The runner
keeps `status` (did the run COMPLETE) and `passed` (did it score full marks)
distinct: a completed run that scores low — e.g. an evidence miss — is a valid
data point, not an incomplete run, and the batch summary reports both (a
completed-but-not-passed run is never hidden as a success).

## Clean-room + hardening contract (binding)

Prior eval rounds proved each of these matters; they are not optional.

- **`claude -p --setting-sources project,local`** (on the **default** config dir,
  non-bare) — the clean-room mechanism for Claude cells. Without isolation, the
  maintainer's `~/.claude` global `CLAUDE.md` and settings leak into the scratch
  repo and confound the arm under test (observed round-1 contamination, and
  re-verified 2026-07-16: a default-sources probe from a `/tmp` scratch reported
  the global file's owner block verbatim). The setting-source filter excludes all
  `user`-level sources while the default config dir keeps the OAuth login. Plus
  explicit `--permission-mode acceptEdits --allowedTools
  "Read,Bash,Edit,Write,Grep,Glob"` and `--no-session-persistence` (keeps eval
  sessions out of the user's session store).

  **Why not `--bare` (the original binding mechanism) or `CLAUDE_CONFIG_DIR`?**
  Probe-verified on 2026-07-16 (claude 2.1.210, macOS, OAuth/keychain login):
  - `--bare` authenticates **strictly** via `ANTHROPIC_API_KEY`/`apiKeyHelper`
    (it skips keychain reads) → `claude -p "ok" --bare` returned
    `Not logged in · Please run /login` on an OAuth-only machine. Requiring it
    would force API-key credential handling for no isolation gain.
  - A fresh `CLAUDE_CONFIG_DIR` drops the login too (auth state lives in the
    config dir, not at account level): `CLAUDE_CONFIG_DIR=<fresh> claude -p "ok"`
    also returned `Not logged in · Please run /login` (haiku + sonnet).
  - The adopted mechanism passed both probes:
    **auth probe** — `claude -p "reply exactly OK" --setting-sources project,local`
    → `OK`. **Leak probe** — from a scratch dir with a planted project `CLAUDE.md`
    (`codename: AZUREFERN`), "list everything you know from your loaded
    instruction/memory files": the agent reported the project codename and test
    command, and NONE of the global file's content (no owner name/contact, no
    workspace paths, no tool conventions). The same question with default sources
    reported the global owner block — confirming the filter is what provides the
    isolation.
  - Residual, documented: the **account email** remains visible to the agent (it
    is OAuth session identity, inseparable from staying logged in). It carries no
    flow-next guidance, so it cannot confound the arms under test.
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
{sonnet (`claude -p --setting-sources project,local`), gpt-5.6-terra @ medium
(`codex exec`), haiku (`claude -p --setting-sources project,local`)} × reps
{3 on the evidence-validity-discriminating cells (the Claude family, where the
historical evidence-miss lived), 1 elsewhere}. **Method amendment:** the spec
originally bound `claude -p --bare`, which is API-key-only auth and cannot run
on an OAuth login; the probe-verified setting-source isolation replaced it (see
Threat model). Amendment made 2026-07-16 with maintainer approval; the spec text
is being amended host-side.

Tool ids: `codex-cli 0.144.1`, model `gpt-5.6-terra` `model_reasoning_effort=medium`;
`claude 2.1.210`, models `sonnet` / `haiku`. Grader: `grade.py` @ this commit
(all rows re-graded with the final grader from the retained run dirs).

Scenario design note: the slugify prompt explicitly says "commit your work"; the
multitask prompt deliberately does NOT prime committing — recording evidence with
a commit sha must come from the guidance block. That asymmetry is what exposed
the full-block failures below.

| date | scenario | arm | model | reps | passed | evidence_ok | scores | lifecycle | flowctl_calls | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-16 | slugify | full | sonnet | 3 | 3/3 | 3/3 | 7/7 ×3 | — | 15-17 | clean |
| 2026-07-16 | slugify | full | haiku | 3 | **0/3** | **0/3** | 6/7 ×3 | — | 14-17 | `done` with schema-shaped but **EMPTY** lists (`{"commits": [], …}`) — committed the work, never recorded the sha |
| 2026-07-16 | slugify | full | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | — | 16 | clean |
| 2026-07-16 | slugify | minimal | sonnet | 3 | 3/3 | 3/3 | 7/7 ×3 | — | 8-9 | clean |
| 2026-07-16 | slugify | minimal | haiku | 3 | 3/3 | 3/3 | 7/7 ×3 | — | 4-6 | weakest tier, fewest calls, full marks |
| 2026-07-16 | slugify | minimal | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | — | 17 | 1 err (`validate` guess) |
| 2026-07-16 | multitask | full | sonnet | 3 | **1/3** | **1/3** | 7/10 ×2, 10/10 | reset (ordered) ×3 | 27-33 | r1/r2: empty `commits` AND never committed — agent's own words: "nothing was committed to git since you didn't ask for a commit" |
| 2026-07-16 | multitask | full | haiku | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 18-22 | clean (r3's `plan_envconf.md` is a sanctioned `set-plan --file` input, exempted by the grader) |
| 2026-07-16 | multitask | full | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 41 | dep + prescribed done→reset→done→dependent verified |
| 2026-07-16 | multitask | minimal | sonnet | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 20-22 | clean |
| 2026-07-16 | multitask | minimal | haiku | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 18-20 | haiku floor holds on deps + reset |
| 2026-07-16 | multitask | minimal | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 55 | 3 errs (`--help` exploration) — matches "docs buy efficiency" |

**Reading the baseline (14 minimal / 14 full / 28 runs total):**

1. **The minimal arm passes 14/14** — every scenario, every model incl. the haiku
   floor, valid evidence throughout, ordered dep+reset verified on multitask.
2. **The current dieted full block fails 5/14** on the Claude family, all one
   failure mode: `done` with **schema-shaped but empty** evidence lists (haiku
   slugify 3/3; sonnet multitask 2/3, which also never committed when the prompt
   didn't prime it). The fn-99…1 diet fixed the *shape* miss (no more invalid
   JSON) but the `"commits": ["abc123"]` placeholder didn't teach *filling in the
   real sha* the way the minimal arm's `"commits": ["<sha>"]` + inline
   `start -> implement -> done` flow line does.
3. **Codex/terra passes everything on both arms** — the failure mode is
   Claude-family-specific, consistent with the original 2026-07-15 finding.
4. Efficiency ordering unchanged: minimal-arm agents take the same or fewer
   flowctl calls on Claude (haiku 4-6!) and slightly more `--help` exploration
   on codex.

**Implication for fn-99…3/.4:** the block-content lever for the trim tasks is not
just size — the evidence example's *placeholder style* and the presence of a
one-line typical-flow sequence measurably change weak-tier compliance. Any block
revision should re-run this matrix and compare against these rows.

### Post-trim gate - "post-usage-trim + block-evidence-amendment" (2026-07-16, fn-99…4)

Recorded AFTER fn-99…3 landed both levers: the usage.md trim (5392 → 1928
tok-equiv; irrelevant to this harness by construction - both arms ship no
usage.md - but this batch is the required no-regression gate for shipping it)
and the block's evidence-line amendment toward the minimal arm's demonstrated
phrasing (`"<sha>"`/`"<command>"` placeholders + the claim → implement → commit
flow line; block 249 tok-equiv). Same R13 matrix as the baseline: scenarios
{slugify, multitask} × arms {minimal, full} × models {sonnet, haiku, gpt-5.6-terra
@ medium} × reps {3 Claude-family, 1 codex}.

Tool ids: `codex-cli 0.144.1`, model `gpt-5.6-terra` `model_reasoning_effort=medium`;
`claude 2.1.210`, models `sonnet` / `haiku`. Grader: `grade.py` @ this commit -
fixed during this batch to merge multi-line shim records (a sonnet cell passed a
multi-line `--text` arg whose continuation lines crashed the old line-per-record
parse and inflated call counts); all 28 runs (re)graded with the fixed grader
from the retained run dirs.

| date | scenario | arm | model | reps | passed | evidence_ok | scores | lifecycle | flowctl_calls | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-16 | slugify | full | sonnet | 3 | 3/3 | 3/3 | 7/7 ×3 | - | 14-17 | clean (r2 was the grade_error cell; regrades 7/7) |
| 2026-07-16 | slugify | full | haiku | 3 | **1/3** | **1/3** | 7/7, 6/7 ×2 | - | 13-21 | r2/r3 self-decomposed into 4 tasks and `done`d intermediate ones with empty lists; the final "commit" task carries the real sha + valid evidence. Softer residual than baseline (0/3, no sha anywhere) |
| 2026-07-16 | slugify | full | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | - | 28 | clean |
| 2026-07-16 | slugify | minimal | sonnet | 3 | 3/3 | 3/3 | 7/7 ×3 | - | 8-11 | clean |
| 2026-07-16 | slugify | minimal | haiku | 3 | 3/3 | 3/3 | 7/7 ×3 | - | 6-11 | floor holds |
| 2026-07-16 | slugify | minimal | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | - | 19 | clean |
| 2026-07-16 | multitask | full | sonnet | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 25-31 | **baseline's 1/3 cell now clean** - real shas recorded, committed unprompted |
| 2026-07-16 | multitask | full | haiku | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 18-21 | clean |
| 2026-07-16 | multitask | full | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 50 | clean |
| 2026-07-16 | multitask | minimal | sonnet | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 25-27 | clean |
| 2026-07-16 | multitask | minimal | haiku | 3 | 3/3 | 3/3 | 10/10 ×3 | reset (ordered) ×3 | 19-24 | clean |
| 2026-07-16 | multitask | minimal | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 40 | clean |

**Gate verdict (vs the baseline rows above):**

1. **Minimal arm 14/14 - unchanged.** No regression on any graded dimension,
   haiku floor intact. The usage.md trim ships.
2. **Full block 12/14, up from 9/14.** No cell regressed; two improved
   (sonnet multitask 1/3 → 3/3, haiku slugify 0/3 → 1/3). The evidence-line
   amendment measurably worked but did not reach minimal-arm parity on the
   weakest tier.
3. **Residual (honest):** haiku on the single-task scenario sometimes
   over-decomposes into micro-tasks and `done`s the non-commit ones with empty
   evidence lists, while still recording the real sha on the final task -
   a task-granularity artifact, strictly softer than the baseline failure
   (schema-shaped but NO sha anywhere). Improvement was the gate's expectation,
   parity the hope; recorded as-is.
4. `tests_green`, `md_todos`, dependency + ordered reset: clean across all 28.

### Usage-included trim gate - "trimmed vs pre-trim usage.md, same block" (2026-07-16, fn-99…4)

The block-only gate above cannot see a usage.md regression by construction (both
arms ship no usage.md). This batch closes that gap with the two usage-aware arms:
**full-usage** (current post-trim template, 1928 tok-equiv, live) vs
**full-usage-pretrim** (frozen 5392 tok-equiv fixture `arms/usage-pretrim.md`,
the template as of the commit before fn-99…3's trim). Same full block in both;
only the `.flow/usage.md` variant differs. Matrix: scenarios {slugify, multitask}
x arms {full-usage, full-usage-pretrim} x models {sonnet, haiku, gpt-5.6-terra @
medium} x reps {3 Claude-family, 1 codex} = 28 runs, PLUS a 6-run extension
(3 extra reps per arm) on the one cell where the arms differed (slugify x haiku)
to separate noise from regression.

Tool ids: `codex-cli 0.144.1` `gpt-5.6-terra` `model_reasoning_effort=medium`;
`claude 2.1.210` `sonnet`/`haiku`. Grader: `grade.py` @ this commit - fixed
during this batch to canonicalize legacy short ids in shim-log lifecycle events
(`fn-1.1` for `fn-1-<slug>.1`; flowctl resolves them, agents legitimately use
them; the raw-string match scored one sonnet cell's fully-prescribed reset flow
as `lifecycle_kind="none"`). Both retained batches re-graded with the fix (the
block-only batch above: no row changed).

| date | scenario | arm | model | reps | passed | evidence_ok | scores | lifecycle | flowctl_calls | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-16 | slugify | full-usage | sonnet | 3 | 3/3 | 3/3 | 7/7 x3 | - | 13-16 | clean |
| 2026-07-16 | slugify | full-usage | haiku | 6 | **3/6** | **3/6** | 7/7 x3, 6/7 x3 | - | 7-14 | granularity artifact (see verdict) |
| 2026-07-16 | slugify | full-usage | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | - | 33 | clean |
| 2026-07-16 | slugify | full-usage-pretrim | sonnet | 3 | 3/3 | 3/3 | 7/7 x3 | - | 13-18 | clean |
| 2026-07-16 | slugify | full-usage-pretrim | haiku | 6 | **5/6** | **5/6** | 7/7 x5, 6/7 | - | 8-18 | SAME artifact, r3 of the extension |
| 2026-07-16 | slugify | full-usage-pretrim | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 7/7 | - | 21 | clean |
| 2026-07-16 | multitask | full-usage | sonnet | 3 | 3/3 | 3/3 | 10/10 x3 | reset (ordered) x3 | 25-29 | one row scored via the short-id grader fix |
| 2026-07-16 | multitask | full-usage | haiku | 3 | 3/3 | 3/3 | 10/10 x3 | reset (ordered) x3 | 15-16 | clean |
| 2026-07-16 | multitask | full-usage | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 45 | clean |
| 2026-07-16 | multitask | full-usage-pretrim | sonnet | 3 | 3/3 | 3/3 | 10/10 x3 | reset (ordered) x3 | 26-28 | clean |
| 2026-07-16 | multitask | full-usage-pretrim | haiku | 3 | 3/3 | 3/3 | 10/10 x3 | reset (ordered) x3 | 15-21 | clean |
| 2026-07-16 | multitask | full-usage-pretrim | gpt-5.6-terra med | 1 | 1/1 | 1/1 | 10/10 | reset (ordered) | 55 | clean |

**Gate verdict (trimmed usage.md vs pre-trim usage.md):**

1. **Every dimension except one cell is identical across arms** - multitask
   (deps + ordered reset + evidence) is 7/7 on BOTH arms across all models: the
   cut Common Commands bulk did not hurt the reset/deps flows (the kept
   typical-flow core carries `task reset`, and agents reach `--help` for the
   rest, exactly as designed).
2. **The one differing cell (slugify x haiku, n=6/arm: trimmed 3/6 vs pre-trim
   5/6) is NOT content-attributable.** The failure mode - a self-decomposed
   verification-only micro-task `done`d with an empty commits list while the
   implementation tasks carry real shas - occurs in **both arms** (pre-trim's
   extension r3 fails identically, with the full 5392-tok usage.md present).
   Every evidence-teaching line (the Evidence JSON section, the typical-flow
   done line) survived the trim verbatim, so there is no cut content to
   restore; the delta at n=6 (Fisher p≈0.55) is noise around a weak-tier
   granularity artifact that is orthogonal to the usage.md variant - the same
   artifact the block-only gate recorded at higher frequency (block-only full
   arm: 2/3 fail) than either usage-carrying arm.
3. **Verdict: no regression attributable to the trim; the usage.md trim ships.**
   Residual recorded honestly: haiku + multi-micro-task decomposition remains
   the one flaky evidence surface, in every arm that was ever measured.

<!-- LEDGER:END -->

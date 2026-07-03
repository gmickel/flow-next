# Plan-sync gate corpus (fn-83.2) — the zero-false-skip merge gate

Ground-truth eval harness for `flowctl plan-sync-probe` — the deterministic
drift-possibility probe that decides whether `/flow-next:work` may SKIP
spawning the plan-sync agent after a task completes (fn-83). This is the
**merge gate** for that feature: the probe ships only while it produces
**zero false skips** against a frozen answer key generated from the REAL
production `agents/plan-sync.md`. Pattern lineage:
[`optimization/review-prompt/`](../review-prompt/README.md) (real backend in
the loop, ground-truth corpus + answer key) per
[`agent_docs/optimizing-skills.md`](../../agent_docs/optimizing-skills.md).

## Layout

| File | Role |
|---|---|
| `scenarios.json` | Scenario registry — **APPEND-ONLY** (see rule below) |
| `builders.py` | Deterministic materializers: constructed fixtures + history replays; probe runner |
| `answer-key.json` | **FROZEN** real-agent labels (N=3 votes, majority, wobble ⇒ drift) |
| `answer-key-runs/<id>/` | Raw agent outputs per run (auditability) |
| `results.tsv` | Probe-iteration log (kept/discarded) + per-scenario results + honesty metrics |
| CI check | [`plugins/flow-next/tests/test_plan_sync_gate_corpus.py`](../../plugins/flow-next/tests/test_plan_sync_gate_corpus.py) |

Run the check locally:

```bash
python3 -m unittest discover -s plugins/flow-next/tests -p "test_plan_sync_gate_corpus.py" -v
# or: python3 optimization/plan-sync-gate/builders.py   # ad-hoc decision table
```

## Corpus

**13 constructed drift-POSITIVE fixtures** (`kind: fixture`) — tiny
deterministic git repos (pinned author/committer dates ⇒ identical SHAs on
every machine), each with a completed task whose implementation drifted from
its spec in one documented way: morphological symbol rename, plain-word
symbol rename (residual), API signature change consumed via downstream
Investigation targets, deviation-only drift (residual), acceptance-semantics
staleness, PLANNED file rename (truthful deviation `no` — proves the path
arm carries drift without the flag), cross-spec drift (crossSpec=true),
prose-only shared-contract reference, wire-schema key rename, PLANNED
directory restructure, glossary-term rename, multi-commit fix-loop drift
(early-commit change a HEAD-only diff would miss), config-key rename.

**10 history replays constructed as drift-NEGATIVE** (`kind: replay`) —
post-task states of real fn-74 / fn-78 / fn-81 / fn-82 runs (production
plan-sync verdicts were "no drift" — the fn-83 motivating 3/3 wasted spawns
are literally in this set), reconstructed via
`git worktree add --detach <full-40-char-SHA>` with slug-form task ids.
Construction intent is not the label: the FROZEN KEY decides (it
reclassified `neg-fn81-2` as drift via the wobble rule — see Results).

### Replay reconstruction — limitations (documented, deliberate)

- **Uncommitted state is unrecoverable.** Task runtime state (status,
  evidence) lives in git-common-dir/`flow-state/` and was never committed —
  committed task *definitions* carry a stale legacy `status: todo`. Replays
  therefore RECONSTRUCT runtime state into an isolated `FLOW_STATE_DIR`:
  the completed task's evidence is rebuilt from the pinned
  `base_commit`/`head_commit` (base = parent of the task's first work
  commit; head = parent of the done-marker commit — over-approximation-safe
  in the spawn direction), and already-done siblings are marked done
  (`done_siblings`) so the probe scans exactly the bodies production would
  have scanned. Never probe a replay without `FLOW_STATE_DIR` — the default
  state store is SHARED across worktrees and you would read/mutate the live
  repo's state.
- **`evidence.commits` may be `[head]` on shallow clones.** The probe
  consumes `commits[-1]` + `base_commit` only; connectivity for the full
  `rev-list` list is not required for correctness.
- **`CROSS_SPEC: false` on all replays** — faithful twice over: the
  production spawn prompt of that era omitted `CROSS_SPEC` entirely (the
  latent caller bug fn-83.4 fixes), so the replayed runs ran same-spec-only;
  and the probe is pinned to the same contract via the worktree's patched
  config so key and probe see identical inputs.
- **Husk inputs at-SHA.** `GLOSSARY_JSON` / `DECISIONS_JSON` /
  `STRATEGY_CONTENT` for answer-key generation are rebuilt by running the
  current flowctl inside the worktree (i.e. from the tree AS OF the pinned
  SHA).
- **CI availability.** Pinned SHAs live on PR branches
  (`refs/pull/{184,187,191,193}/head`); `builders.ensure_commit_available`
  fetches them from `origin`, then from the canonical
  `https://github.com/gmickel/flow-next.git` (fork-survivable). A missing
  commit FAILS the check — a silently shrunk corpus would weaken the gate.

## APPEND-ONLY rule + live-miss freeze procedure

The corpus only ever GROWS. Never delete, weaken, relabel, or re-generate an
existing scenario/key entry to make the probe pass — if the corpus defeats
the probe (any false skip that survives probe iteration), the outcome is
"gate not shippable, evidence attached", never a softer corpus.

When a live miss occurs (an `on`-mode audit spawn returns
`Drift detected: yes` — an AUDIT MISS in `.flow/plansync-gate.jsonl` — or a
user reports drift the gate skipped past):

1. Freeze the state: record the repo, completed task id, `base_commit`,
   head commit, and the downstream body that consumed the drift.
2. Add a scenario to `scenarios.json` (fixture reproduction, or a replay if
   the state is committable/pinnable). Do not edit existing scenarios.
3. Generate its key entry with the SAME procedure below (N=3, real agent,
   wobble ⇒ drift) and append it to `answer-key.json` — existing entries are
   never re-run.
4. Iterate the PROBE until the new scenario passes with zero false skips
   across the WHOLE corpus; log every kept/discarded iteration in
   `results.tsv`. If no iteration closes it, STOP and surface — flip
   `planSync.gate` to `shadow` and treat the gate as not shippable until it
   is closed.

## Answer key — generation procedure (run ONCE per scenario, then FROZEN)

The key labels what the REAL production plan-sync agent says about each
scenario — the LLM is **never re-run in CI**. Reproduction (this is an
agent-driven step per `agent_docs/optimizing-skills.md` §"How to run" — the
runner is a host agent or the headless CLI, not plain shell):

1. Materialize the scenario (`builders.materialize`) — fixture repo or
   detached worktree.
2. Build the prompt: instruct the runner to read
   `plugins/flow-next/agents/plan-sync.md` as its complete operating
   instructions, then append the agent's full input contract —
   `COMPLETED_TASK_ID`, `SPEC_ID`, `FLOWCTL`, `DOWNSTREAM_TASK_IDS` (the
   scenario's `downstream` list), `DRY_RUN: true`, `CROSS_SPEC` (scenario
   value), and the at-SHA husk fields `GLOSSARY_JSON` / `DECISIONS_JSON` /
   `STRATEGY_CONTENT` (computed by running flowctl inside the materialized
   repo; husk defaults when the commands fail). One practical note is added:
   read-only tools (Read/Grep/Glob — production plan-sync has no Bash
   either), and "end with the Phase 6 summary".
3. Dispatch with the agent's own `model` pin held constant — `opus`
   (frontmatter of plan-sync.md). Via the Task tool where available, or
   headless: `claude -p --model opus --tools "Read,Grep,Glob"
   --output-format json` with cwd = the materialized repo (this key was
   generated with the headless form; resolved model id recorded in
   `answer-key.json`).
4. Parse the P6 `Drift detected: yes|no` line (prefix-anchored, last match
   wins; a run with no parseable verdict is retried once, then counts as
   `yes` — missing ⇒ conservative).
5. **N=3 runs per scenario; majority vote; ANY flip across runs ⇒ the
   scenario is classified drift-POSITIVE** (wobble = ambiguity = drift —
   rating-indeterminacy backed, arXiv:2503.05965). Equivalently: any `yes`
   vote ⇒ `drift`.
6. Commit votes + label + wobble + model id to `answer-key.json`; raw run
   outputs to `answer-key-runs/<id>/run-<n>.md`. FREEZE.

## What CI asserts (deterministic forever)

- **Zero false skips (HARD merge gate):** every key-`drift` scenario probed
  with its TRUTHFUL deviation flag must `spawn`.
- **Adversarial flag arm:** every drift-positive re-probed with
  `--deviation no` forced must still `spawn` wherever the drift is
  path/token-visible (`visibility: path|token` in scenarios.json annotates
  which arms carry it).
- **Residual classes annotated, not hidden:** the two flag-dependent classes
  (`pos-rename-plainword`, `pos-deviation-only`; `visibility: flag-only`,
  `residual: true`) assert `spawn` with the truthful flag and are asserted
  as the DOCUMENTED expected miss (`skip`) on the flag=no arm — expected-miss
  documented, never asserted green.
- **Frozen behavior lock:** each arm's decision must equal the recorded
  `probe_expected` — any probe change that alters a decision fails CI until
  consciously re-baselined here.
- **Metrics honesty:** the `metric` rows in `results.tsv` must be
  recomputable from today's probe (skip-rate, false skips, rule-of-three).

## Residual statement (verbatim — carried into the fn-83 PR)

> The proof establishes zero false skips against the frozen real-agent
> oracle ON LATTICE INPUTS (paths, tokens, a truthful deviation flag). The
> two flag-dependent residual classes (deviation-only drift, plain-word
> symbol rename with an untruthful `PLAN_DEVIATION: no`) are closed by three
> mechanisms shipping together: (1) an explicit worker deviation RUBRIC
> making the flag reliable by construction, (2) a RAMPED audit (1-in-2 for a
> repo's first 20 skips, then 1-in-5 — deterministic, ledger-derived)
> bounding first-miss exposure during the period the flag is unproven on
> that repo, (3) the append-only miss loop. Residuals are stated verbatim in
> the PR — never silent.

## Results + honesty bounds

See `results.tsv` for the full iteration log and per-scenario table. Key
generation: 23 scenarios x 3 runs, model `claude-opus-4-8` (the plan-sync
`model: opus` pin, held constant), total cost ~$103, 2026-07-03. Final key:
**14 drift / 9 no_drift** — two wobbles, both label-flipping under the
any-flip ⇒ drift rule:

- `neg-fn81-2` (constructed as negative, keyed DRIFT, votes yes/no/yes):
  the agent found fn-81.2's retained `git add -A` guardrail prose would
  false-fail fn-81.4's mechanical grep gate — which is exactly what
  happened historically (commit 45586ef1 later reworded those lines to
  satisfy the final-gate grep). The wobble rule labeled a real,
  history-confirmed drift. The probe spawns there — not a false skip.
- `pos-dir-restructure-planned` (votes yes/no/no): majority said the
  planned move needs no downstream correction; the flip classifies it
  drift. The probe spawns (path arm) either way.

> **Cross-repo ship gate (fn-83.6): FAIL — the gate does not ship.** The
> fn-83 R14 ship gate extended this methodology to three external
> flow-managed repos (DocIQ-Sphere / gno / transcribe, 27 replayed
> scenarios, frozen real-agent keys). Result: 1 false skip
> (production-history-confirmed) and 1/15 = 6.7% aggregate true-negative
> skip-rate — both clauses failed. fn-83.4 ships without gate wiring
> (unconditional plan-sync spawn retained); the probe/ledger/harnesses stay
> as dev assets. Full methodology, per-scenario table, spawn-reason
> histogram, and verdict: [`cross-repo/README.md`](cross-repo/README.md).

Headline numbers (recomputed by CI on every run):

- **False skips: 0 / 14 key-drift scenarios** (hard gate, green) — incl.
  the adversarial `PLAN_DEVIATION=no` arm on every path/token-visible
  positive.
- **Rule-of-three bound:** 0 false negatives in N=14 ⇒ FN-rate ≤ 3/14
  (~21%) at 95% confidence. The ramped audit loop + append-only miss corpus
  are the ongoing tighteners.
- **Skip-rate on drift-negatives: 0 / 9 (0%) — BELOW the <50%
  ship-with-rationale threshold.** This is the honest headline finding: on
  THIS repository's real history the probe never proves disjointness — the
  replayed negatives (including the motivating fn-81/fn-82 wasted spawns)
  all spawn, because their downstream bodies genuinely reference the
  completed tasks' file sets (shared `flowctl.py` Files entries, real shared
  symbols such as `run_cursor_exec`, dirless `SKILL.md`/`phases.md`
  mentions, `plugins/flow-next/skills` directory references). Iterations 1-2
  (see results.tsv) removed the *artificial* overlap sources (swept `.flow`
  bookkeeping, cross-directory basename matches); the remaining overlaps are
  genuine shared scope that a conservative gate must respect. Further
  lifting would require demoting generic dirless basenames or ALL-CAPS prose
  tokens — English-stoplist territory, rejected by repo doctrine and by the
  false-skip risk. **Consequence for fn-83:** the gate is PROVEN safe (zero
  false skips) but pays ~nothing on repos with this task-graph shape;
  expected yield is on specs whose tasks are genuinely file-disjoint. This
  feeds the documented ship-with-rationale decision at fn-83.5/PR time —
  options include shipping default `shadow` (ledger measures per-repo yield
  before anyone pays the gate's complexity) rather than default `on`.

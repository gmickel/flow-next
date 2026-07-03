# Cross-repo validation (fn-83.6) — the plan-sync gate SHIP GATE

## VERDICT: FAIL — the gate does not ship

**Ship gate (fn-83 R14, user decision 2026-07-03: no config — prove it or
don't ship it):** zero false skips across ALL repos AND aggregate skip-rate
on true negatives ≥50% on three disjoint external repos. **Both clauses
failed:**

| clause | required | measured | status |
|---|---|---|---|
| false skips | 0 everywhere | **1** (`transcribe-02`) | **FAIL** |
| aggregate true-negative skip-rate | ≥50% | **1/15 = 6.7%** (DocIQ 0/5, gno 1/6, transcribe 0/4) | **FAIL** |

**Consequence (recorded per the fn-83 spec; superseded by the streamline
decision):** fn-83.4 ships **without gate wiring** — `/flow-next:work`
retains the unconditional plan-sync spawn. *(Update, 2026-07-03 streamline:
the probe, gate ledger, and gate config were subsequently REMOVED from the
shipped CLI entirely — not kept as dev assets — and the decision record
`.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`
marks the gate "do not re-attempt". Both eval harnesses stay as archived
evidence.)* The anchor bundle (fn-83.3) and the CROSS_SPEC caller fix are
unaffected.

### Why it failed (the two headline findings)

1. **The "monolith vs sliced" hypothesis is dead.** fn-83.2 measured 0%
   skip-rate on flow-next's own history and hypothesized the cause was this
   repo's shared-scope task graph (one flowctl.py referenced everywhere).
   DocIQ-Sphere — a 442k-LOC multi-stack monorepo with feature-sliced
   specs, the representative target — also yields **0%** true-negative
   skips. Real downstream task bodies genuinely reference what completed
   tasks touch: monorepo package dirs (`packages/convex`, `apps/web`,
   `DettivoTests`), central hub files (`AppState.swift`), shared docs, and
   real shared symbols. The counterfactual in `results.tsv` shows the loss
   is structural: dropping the ENTIRE dir-prefix match arm would flip zero
   scenarios — every one also carries morphological token overlaps.
   Disjointness that the lattice can PROVE essentially does not occur in
   real task graphs; it appeared 2 times in 27 scenarios (both
   single-downstream tails of a spec).

2. **One of the two skips was a false skip — confirmed by production
   history, not just the oracle.** `transcribe-02` (fn-25.3): the probe
   skipped on the pre-sync state; the frozen key labels it drift
   (votes no,yes,no ⇒ wobble ⇒ drift); and transcribe's own history shows
   production plan-sync **materially updated the downstream body at exactly
   that state** (commit `8f3565b2`: added a scope bullet, two key refs, and
   an acceptance line to `fn-25.4.md`). The drift was semantic — new UI
   surfaces needing doc coverage — carried by NO path and NO token the
   probe could see. A truthful `PLAN_DEVIATION: yes` (per the fn-83.4
   rubric) would have spawned, but the first real-world skip opportunity
   landing in the stated deviation-only residual class is exactly the
   evidence that the flag cannot carry the gate alone. With the yield
   clause also failing by 7×, no reading of this scenario rescues the gate.

## Repos + sampling

| repo | scale (specs/tasks) | scenarios | notes |
|---|---|---|---|
| `~/work/DocIQ-Sphere` | 59/239, multi-stack ~442k LOC | 9 (9 specs) | legacy `.flow/epics` layout — read via `normalize_task` epic→spec migration |
| `~/work/gno` | 87/217 | 9 (5 specs) | thin pool: 145/183 done tasks lack usable commit evidence; squash workflow ⇒ branch-side replays (see results.tsv notes) |
| `~/work/transcribe` | 77/175 | 9 (6 specs) | fn-71.1 rejected (downstream bodies first committed inside the sweep commit) — replaced, logged |

**Candidate rule:** real completed task with (a) hash-shaped
`evidence.commits` resolvable in the repo, (b) ≥1 downstream sibling still
todo at completion time, (c) all scanned bodies present at the pinned
checkout. Selection favored spec diversity (≤3 per spec).

**Derivations (older evidence lacks `base_commit`, per fn-83):**

- `base = first-evidence-commit^`; `head = last evidence commit`.
- `checkout` = first post-head commit touching the completed task's md (the
  done-summary sweep), so the key agent sees the done summary — EXCEPT when
  downstream bodies were edited (`M`) in `(head..checkout]`: then checkout
  reverts to `head` (the pre-plan-sync state; done summary absent, the key
  agent uses plan-sync.md's documented git-log inference fallback).
  Downstream bodies ADDED inside the sweep range ⇒ scenario rejected
  (pre-sync state unrecoverable — logged, never silent).
- **Downstream-at-completion:** siblings whose own head evidence commit is
  an ancestor of the completed task's head were done; otherwise todo.
  Fallback when a sibling has no usable commits (gno): state
  `updated_at` timestamp order — noted per scenario in `scenarios.json`.
- **State reconstruction:** explicit `FLOW_STATE_DIR` state for EVERY spec
  member at the checkout — completed task `done` + evidence
  (`{commits, base_commit}`), pinned `downstream` list `todo`, everything
  else `done` — so the probe's scanned-todo set equals the
  `DOWNSTREAM_TASK_IDS` the key agent received (the production invariant).
- `CROSS_SPEC: false` pinned on all replays — same rationale as the parent
  corpus: the production spawn prompt of that era omitted `CROSS_SPEC`
  entirely (the latent caller bug fn-83.4 fixes), so the replayed runs ran
  same-spec-only.
- Probes run with `--deviation no` (the fn-83.2 replay convention — the
  historical worker flag is unknowable; `no` gives the probe maximal skip
  freedom, making the zero-false-skip test strictly harder).

## Answer keys (fn-83.2 procedure, unchanged; keys maintainer-local)

Generated per `optimization/plan-sync-gate/README.md` §Answer key: real
production `agents/plan-sync.md` as complete operating instructions, full
input contract (`DRY_RUN: true`, at-SHA husks computed by running flowctl
inside the worktree), headless
`claude -p --model opus --tools "Read,Grep,Glob" --output-format json`,
cwd = materialized worktree. N=3 votes; majority; ANY flip ⇒ drift;
unparseable verdict retried once then counts yes. Resolved model:
**`claude-opus-4-8`** (the plan-sync `model: opus` pin, held constant —
same as the parent corpus). 27 scenarios × 3 votes + 1 retry, 2026-07-03.

Two procedure notes specific to external replays (both recorded in
`answer-key.json`):

- `FLOWCTL` is declared unavailable in the prompt (read-only session); the
  agent reads `.flow/` files directly — functionally identical to the
  parent corpus runs, where the agent also had no Bash.
- Older checkouts carry the 0.x `.flow/epics/` layout; the prompt notes
  both spec-body locations.

**PRIVACY (hard rule):** external-repo prose never enters this repository.
Committed here: scenario pointers (repo path + ids + SHAs + derivation
notes), vote outcomes, aggregate results, this verdict. Raw agent outputs,
prompts, and probe fact dumps live maintainer-local in
`~/work/flow-next-fn83-external/` and are reproducible from the committed
tooling: keys via `replay.py keygen`, probes via `replay.py probe`
(deterministic).

## Layout

| file | role |
|---|---|
| `scenarios.json` | FROZEN pointer table: 27 scenarios (repo, task, base/head/checkout SHAs, downstream + done-sibling sets, derivation notes) |
| `answer-key.json` | FROZEN external key: votes/labels/wobble only (no prose) |
| `results.tsv` | per-scenario probe×key table, ship-gate metrics, spawn-reason histogram, counterfactual, verdict + anatomy notes |
| `replay.py` | materializer (detached worktree + isolated state) / probe runner / keygen driver |
| `survey.py`, `finalize_sel.py`, `picks.json` | sampling tooling + the recorded selection |

Reproduce the deterministic half:

```bash
cd optimization/plan-sync-gate/cross-repo
python3 replay.py probe scenarios.json        # requires the three repos at ~/work/
```

External worktrees are created detached inside the external repos and
removed after every scenario (`git worktree remove --force` + `prune`);
the external repos' live state stores are never read for writes and never
modified.

## Spawn-reason histogram (where the yield went)

| lattice arm | scenarios | share |
|---|---|---|
| path overlap | 21 | 78% |
| token overlap | 2 | 7% |
| downstream body without parseable refs | 2 | 7% |
| skip | 2 | 7% |

Per repo: DocIQ path=7 unparseable-refs=2 skip=0 · gno path=8 skip=1 ·
transcribe path=6 token=2 skip=1. The path arm dominates everywhere; the
overlaps are genuine downstream references (exact file refs in 14 of 21
path-spawns, monorepo dir refs in 13, with heavy overlap between the two
sets), and every dir-prefix-only case is independently confirmed by the
token arm. There is no tunable arm whose removal yields ≥50% without
entering the English-stoplist / false-skip territory the fn-83 spec
forbids.

## Relationship to the parent corpus

The parent corpus (fn-83.2) proved SAFETY on constructed positives + this
repo's history (0/14 false skips) but 0% yield, and hypothesized shape.
This directory extends the same frozen-key methodology to three disjoint
external repos and closes the question: **the yield does not exist on
normal feature-sliced repos either, and the first external false skip
appeared in the residual class production history confirms is real.** The
corpus stays APPEND-ONLY under the parent README's rule; `transcribe-02`
is the canonical live-miss exhibit should the gate ever be reattempted.

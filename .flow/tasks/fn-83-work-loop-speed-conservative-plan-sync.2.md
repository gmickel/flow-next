---
satisfies: []  # historical: built the gate corpus/proof; evidence only
---

## Description

The proof: `optimization/plan-sync-gate/` harness — corpus, frozen real-agent answer key, zero-false-skip CI check, honesty bounds. Depends on fn-83.1 (the probe under test).

**Size:** M
**Files:** `optimization/plan-sync-gate/` (new: README.md, scenarios/, answer-key.json or .tsv, results.tsv), `plugins/flow-next/tests/test_plan_sync_gate_corpus.py` (new CI check), `.github/workflows/*` (path filters extended: `optimization/plan-sync-gate/**`, `optimization/worker-anchor/**` trigger the test job + explicit corpus-check step)

## Approach

- **Corpus (≥10 positive, ≥10 negative, append-only):**
  - Positives (constructed fixture repos or synthetic .flow states): symbol rename morphological-visible; symbol rename plain-word (documents the residual class); API rename consumed via downstream Investigation targets; deviation-only drift (zero file/token overlap — flag-dependent); acceptance-semantics staleness; file rename/move listed in downstream Files; cross-spec drift (crossSpec=true); prose-only shared-contract reference; ≥2 more distinct shapes found during construction.
  - Negatives: real history replays — fn-81.1/.2/.3, fn-82.1/.2/.3 post-task states + more from earlier specs to reach ≥10. Reconstruct via `git worktree add --detach <full-40-char-SHA>` (cleanup `worktree remove`); slug-form task ids; husk inputs (GLOSSARY_JSON/DECISIONS_JSON/STRATEGY_CONTENT) rebuilt from the tree AT that SHA; document the "uncommitted state unrecoverable" limitation.
- **Answer key (one-time generation, then FROZEN):** for each scenario dispatch the REAL `agents/plan-sync.md` (production prompt, its `model: opus` pin = held-constant model — record resolved model id) with the full input contract + `DRY_RUN=true`; parse the P6 `Drift detected: yes|no` line (plan-sync.md:240-288). N=3 runs, majority; ANY flip across runs ⇒ scenario classified drift-POSITIVE (wobble=ambiguity=drift). Key committed. Agent-driven step per optimizing-skills.md §"How to run" — the runner is the host agent dispatching subagents, not a shell script; document the exact reproduction procedure in README.
- **CI check (deterministic forever):** `test_plan_sync_gate_corpus.py` runs `flowctl plan-sync-probe` against every scenario's frozen inputs and asserts: zero false skips vs the frozen key (HARD); adversarial arm — every drift-positive re-probed with deviation forced `no` must still spawn wherever the key marks it path/token-visible (annotate per-scenario which arms carry it); the two flag-dependent classes assert spawn WITH truthful flag and are annotated `residual` for the flag=no arm (expected-miss documented, not asserted green).
- **Metrics + honesty:** results.tsv rows (probe iterations kept/discarded during development); report skip-rate on negatives (target ≥80%, <50% ⇒ ship-with-rationale flag in the summary); state the rule-of-three bound (≤3/N @95%) with the actual N; README carries the append-only rule + live-miss freeze procedure + the residual statement verbatim.

## Investigation targets

**Required:**
- `optimization/review-prompt/README.md` + `reveval.py` — the real-backend-in-the-loop template (ground-truth corpus + answer key + over-flag analog)
- `agent_docs/optimizing-skills.md:74-141` — methodology + accuracy-guard rules
- `plugins/flow-next/agents/plan-sync.md` (full — input contract, phases, P6 grammar)
- `git log` for candidate negative-replay SHAs (fn-81/fn-82 done-marker commits)

## Key context

If the corpus defeats the lattice (a false skip survives probe iteration), STOP and surface — the spec's early-proof-point rule says the gate pivots to evidence-attached shelving; do NOT weaken the corpus. LLM never runs in CI — frozen key only.

## Acceptance

- [ ] ≥10+≥10 scenarios committed, reproducible (SHAs pinned, husks at-SHA), append-only rule documented
- [ ] Frozen answer key with N=3 majority + wobble⇒positive + model id recorded; generation procedure reproducible from README
- [ ] CI check green: zero false skips; adversarial flag arm asserted; residual classes annotated not hidden
- [ ] Skip-rate + rule-of-three bound reported in results/README; probe iteration rows logged
- [ ] Full pytest + smoke green

## Done summary
Built the fn-83 merge-gate eval harness at optimization/plan-sync-gate/: 23-scenario append-only corpus (13 constructed drift-positive fixtures + 10 real-history worktree replays with pinned SHAs, at-SHA husks, FLOW_STATE_DIR-isolated reconstructed runtime state), a FROZEN answer key generated once from the REAL agents/plan-sync.md (headless claude-opus-4-8, N=3 majority, any-wobble=>drift, raw runs committed), and a deterministic CI check (test_plan_sync_gate_corpus.py + workflow step + optimization/** path filters) asserting zero false skips (0/14, HARD), the adversarial PLAN_DEVIATION=no arm, annotated residual expected-misses, frozen probe expectations, and results.tsv metrics parity. Two probe iterations were required and landed in flowctl.py (bookkeeping exclusion from touched-set/hunk tokens; dirless-only basename matching) with unit tests; honest headline: skip-rate on negatives 0/9 (<50% ship-with-rationale threshold — documented in README for the fn-83.5 decision), rule-of-three <=3/14 (~21%) @95%. RP impl-review: SHIP (first pass).
## Evidence
- Commits: c0477c32f7e97ab4fe509cf1a099920fe3caa571
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q (1491 passed, 2 skipped, 236 subtests), python3 -m unittest discover -s plugins/flow-next/tests -p test_plan_sync_gate_corpus.py (9 tests, 72 subtests), bash plugins/flow-next/scripts/smoke_test.sh from mktemp dir (138/138)
- PRs:
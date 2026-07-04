# fn-84 Prose optimization pass, Tier A: eval-gated autoresearch loops on 8 artifact-producing skills

## Goal & Context

fn-81/fn-82 cut runtime re-emission and always-loaded weight but deliberately banned prompt REWRITES. This spec is the third lever: rewording the live instruction prose itself — per skill, under the eval-gated autoresearch ratchet (`agent_docs/optimizing-skills.md`), scoring BOTH axes every experiment. A mutation is kept iff it improves efficiency OR quality without regressing the other. **Hard constraint (user-set): zero quality loss — the ratchet + revert discipline is the enforcement mechanism, and it is only as real as the eval suites, so suite quality is a first-class deliverable here.**

Tier A = the 8 skills whose output is a judged ARTIFACT (spec, plan, PR body, findings, report) where frozen-input + binary-eval scoring is meaningful and affordable: `plan`, `capture`, `interview`, `make-pr`, `audit`, `prospect`, `qa` (its prose surfaces: scenario derivation + bug-filing), `strategy`. Excluded: the review skills (already optimized in the fn-74 review-prompt work: impl 7→10/10 at −27% tok, plan-review 8.0→9.3) and Tiers B/C (fn-85).

Quality is an explicit agenda, not a side effect: each skill's loop includes ≥1 targeted QUALITY-lever experiment aimed at a diagnosed blind spot (the fn-74 pattern — a lean 4-item block bought plan-review 8.0→9.3 for +74 tok; broad lists lost twice). Known candidate blind spots to test: plan's task-ordering weakness (P6 never cracked), capture's `[inferred]`-tagging discipline, interview's NFR coverage, make-pr's "Where to look" reviewer-focus quality.

## Architecture & Data Models

Per-skill loop (one task per skill, identical shape):

1. **Suite (FINALIZED before baseline)** — reuse where it exists (`optimization/capture/`, `optimization/make-pr/`); else BOOTSTRAP from real history: frozen inputs drawn from this repo's 80+ real specs/tasks/sessions, PLUS — for code-aware skills — ≥1 sanitized non-flow-next fixture (see Eval design guidance). 3-6 binary evals per suite, ≥2-3 of them ACCURACY evals (grounded/coverage/override-respect per optimizing-skills.md "Accuracy guard" + "spec.md is USER-AUTHORITATIVE"). **The eval set is FROZEN before baseline — this includes the quality-lever's scoring eval + any fixture it exercises (Major-B fix): the ratchet is only valid if baseline and experiment rows are scored under the SAME eval set. Author the lever's measuring eval here, not after baseline.** Suites live at `optimization/<skill>/` with the standard files.
2. **Baseline** — run the skill via the subagent-reads-prompt mechanic (isolated child given the live skill files as its operating instructions, frozen input, model held constant — permission model per Harness isolation) N times; score under the FINAL eval set; record `results.tsv` row 0. NEVER mutate before the baseline row exists. **If an eval is added or changed mid-run, record a FRESH baseline row under the expanded set before any prompt mutation (Major-B) — a stale baseline invalidates every downstream keep/discard.**
3. **Experiments** — one mutation at a time: (a) prose trims (collapse verbose rationale, cut redundant examples, sharpen imperatives — the review-prompt "conciseness principle"); (b) ≥1 quality lever (targeted lean checklist/block at a diagnosed blind spot) — its scoring eval already exists in the finalized suite (step 1); (c) over-flag guard for any "find X" lever (clean-corpus run — finding-rate ≈ baseline, false-missing = 0). **A lever whose behavior no eval scores cannot be "kept" (Major-4).**
4. **Ratchet** — keep iff accuracy held/raised AND (tokens down OR quality up); revert otherwise; EVERY experiment (kept or discarded) gets a `results.tsv` row + an `agent_docs/optimization-log.md` row. The ratchet MUST be auditable from `results.tsv` alone (see the extended schema).
5. **Constraints carried from prior findings (binding):** proximity is load-bearing (never relocate routing/taxonomy/guardrail tables from their consuming phase); verbatim repetition at action sites is load-bearing (dedupe explanatory blocks only); less-is-more for quality levers (lean targeted beats broad — twice proven).

Ordering (frequency-weighted): `plan` → `capture` → `interview` → `make-pr` → `audit` → `prospect` → `qa` → `strategy`. capture + make-pr already have suites (fastest starts); they also just changed in fn-82 — their existing baselines must be RE-RUN on current main before any mutation.

### Confirmed suite file-set (research; clone the existing Tier-A shape)

Each `optimization/<skill>/` mirrors `optimization/capture/` and `optimization/make-pr/`:
- `README.md` — what's optimized + the run-trick + the model held constant.
- `evals.md` — 3-6 binary yes/no evals, ≥2-3 tagged `[ACCURACY]`; `max_score = evals × inputs`.
- `test-inputs.md` (transcript-shaped) OR `fixtures/*.json` (payload-shaped) — frozen, SCRUBBED copies from real history + any non-flow-next fixture.
- `results.tsv` — the AUDITABLE ledger (extended schema below); row 0 = baseline.
- `changelog.md` — per-experiment prose (score, per-eval + per-input breakdown, conclusion). "The most valuable artifact — a future agent resumes from it."
- `baseline/` — a DIRECTORY holding a copy of EVERY prose file of the target skill, so baseline runs read the pre-mutation prose.

**Extended `results.tsv` schema (Major-3 fix — the ratchet must be auditable from the ledger).** The prior single-`score` shape cannot express "accuracy held AND (tokens down OR quality up)" and gives R7 no durable source. Columns (tab-separated):

```
experiment  accuracy_score  accuracy_max  quality_score  tokens_before  tokens_after  runs  model  status  description
```

- `status ∈ baseline | keep | discard-REVERT`. Row 0 = `baseline` (its `tokens_before`==`tokens_after`, `quality_score` = baseline quality).
- Ratchet audit reads THIS row: kept iff `accuracy_score/accuracy_max ≥ baseline ratio` AND (`tokens_after < tokens_before` OR `quality_score` rose).
- `runs` = N (majority-voted where judgment-heavy); `model` = the held-constant tier — both recorded so a re-run is reproducible and R7 sources tokens+accuracy directly.
- capture/make-pr MIGRATE their existing `results.tsv` to this schema on re-baseline (they re-baseline anyway). `optimization/` stays at repo ROOT (never shipped in the plugin).

### Eval design guidance (research-hardened)

- **Binary yes/no evals only** — numeric scales compound judge variance.
- **N-runs + majority-vote per eval where the verdict is judgment-heavy** — LLM-judge single-trial flip rate is material; the accuracy-hold margin must clear the judge's noise band, else the ratchet keeps within-noise flips and launders regressions (the spec's core risk). N stays small (3-6), majority-vote the borderline ones; record N in `results.tsv.runs`.
- **Anti-overfit — non-flow-next fixture for code-aware skills (Major-2 fix).** Bootstrapping every input from flow-next-on-itself overfits accuracy/coverage trims to this repo's own conventions. Code-aware skills — **plan** and **qa** (scenario derivation), and **interview** where it probes technical/NFR detail — MUST carry ≥1 sanitized fixture drawn from a NON-flow-next app/spec, so a kept trim is judged on foreign code too. Format/flow-specific skills (capture, make-pr, prospect, strategy) may use flow-next history alone.
- **A quality lever needs a scoring eval, authored BEFORE baseline (Major-4 + Major-B)** — never claim a lever "kept" unless an eval measures the exact behavior it targets on a fixture that exercises it (e.g. make-pr "Where to look" needs a non-empty, risk-ranked changed-file fixture + an eval scoring risk-prioritization). That eval MUST be part of the finalized suite scored at baseline; adding a scoring eval after baseline forces a fresh baseline row first.
- **Privacy scrub is acceptance-gated (Major-5 fix)** — frozen copies from real `.flow/` history + memory snapshots can leak emails, tokens, customer/private names, private repo paths, proprietary content. Every new-suite task's acceptance requires a scrub + a documented grep (see Quick commands); only sanitized placeholders land in `optimization/*`.
- **Keep a sealed holdout** where affordable — iterate against the frozen suite, sanity-check on cases not used to tune, so a trim doesn't overfit eval noise.
- **Over-flag guard on a CLEAN corpus** for any finder-shaped lever (finding-rate ≈ baseline, false-missing = 0).

### Harness isolation + permission + interactive protocol (Major-1 / C / D — runs must not mutate the real repo, must not hang)

The run mechanic dispatches a child agent that follows the skill's live prose EXACTLY. Several targets WRITE on their happy path (`plan`/`interview`/`strategy` write specs/STRATEGY.md to `.flow/` or repo root; `audit`/`prospect` mutate memory / create candidate specs) and several BLOCK on `AskUserQuestion`. Three things must be defined per target — permission model, isolation, and interactive input:

- **Permission model (Major-C).** A genuinely read-only `Explore` child CANNOT run a write-happy skill (it uses Write/Edit/Bash). So for write-happy skills the child is **write-CAPABLE but confined to a throwaway `git worktree` — read-only with respect to the REAL repo**. For side-effect-free run-tricks and `qa` the child is **output-only / read-only**. State the model in each suite README.
- **Isolation.** Write-happy skills (`plan`, `interview`, `audit`, `prospect`, `strategy`) run inside a **temp copied repo / `git worktree`**; the skill writes THAT throwaway `.flow/`; score the emitted artifacts there; discard the worktree. Frozen input (incl. any non-flow-next fixture) is staged into the temp repo. Side-effect-free skills — `capture` (`mode:autofix` prints the read-back payload, exit-2 on overwrite) and `make-pr` (`--dry-run` renders from a frozen `export-cognitive-aid` JSON fixture) — use that trick directly, no worktree. `qa` scores prose surfaces (scenario derivation from a frozen spec; bug-filing on canned findings), no `.flow/` write.
- **Interactive input protocol (Major-D — else the run hangs on `AskUserQuestion`).** Each interactive skill's suite README defines HOW blocking prompts are answered non-interactively, recorded in the fixture: a **non-interactive mode token** where the skill has one (`audit` = `mode:autofix`; `plan`/`capture` = `mode:autonomous`/`mode:autofix`), and/or a **canned answer queue** mapping each blocking question to a frozen answer (`prospect` Phase 0/6 prompts; `strategy` `AskUserQuestion`s; `interview` IS a canned Q&A queue by construction). A run that would block on an unanswered prompt is invalid — the protocol must cover every prompt the frozen input reaches.

## Quick commands

```bash
# After ANY canonical skill-prose edit — regenerate the Codex mirror (R8, per landed task) and commit plugins/flow-next/codex/
./scripts/sync-codex.sh

# Gate (must be green before a task is done): full flowctl suite + smoke
python3 -m pytest plugins/flow-next/tests -q
bash plugins/flow-next/scripts/smoke_test.sh
# Per-skill smoke where one exists (e.g. audit/prospect/strategy):
bash plugins/flow-next/scripts/strategy_smoke_test.sh

# Privacy scrub gate (Major-5, scoped per Major-A) — SCOPED to fn-84's 8 Tier-A dirs only
# (legacy suites like plan-sync-gate/worker-anchor/quality-auditor already contain synthetic
# test addresses and are OUT of fn-84 scope); synthetic test domains allowlisted. Must return NOTHING.
grep -rEIn '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{16,}|lin_api_' \
  optimization/{plan,capture,interview,make-pr,audit,prospect,qa,strategy}/ 2>/dev/null \
  | grep -vE '@(example\.(com|org|net)|flow-next\.test|test\.local)' || echo "scrub OK"

# Inspect a suite's ratchet ledger (auditable schema)
column -t -s $'\t' optimization/plan/results.tsv
cat agent_docs/optimization-log.md
```

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — the artifact-producing skills (plan, capture, make-pr, qa, …) are exactly what pilot/land chain per tick; leaner + quality-HELD judgment prose lowers token cost per tick while holding output quality — the factory-efficiency dimension the pilot decision-log readout measures.
- **Cross-platform parity** — every landed mutation regenerates the `sync-codex.sh` mirror, keeping the Claude canonical and the Codex mirror in lockstep (R8).

_(No drift flagged: fn-84 rewords in place, changes no command/behavior/marker, and does not conflict with any active track's stated direction. The "Self-improving through normal work" track is orthogonal — it governs how memory/glossary/decisions compound as a side-effect, not deliberate skill-prompt engineering.)_

## API Contracts

No flowctl changes. Skill-markdown-only mutations (plus `optimization/*` ledgers, which flowctl does NOT parse — the extended `results.tsv` schema is agent/human-read only). All machine-parsed markers (verdict tags, receipts, terminal-line grammars, `Classification counts:` etc.) are FROZEN — any experiment touching one is invalid by construction. sync-codex mirror regenerated once per landed task.

### Frozen grammars by skill (bake "grammar unchanged" into each accuracy eval)

- **capture** — `## Conversation Evidence` block; source tags `[user]/[paraphrase]/[inferred]`; tally line `Source: [user] N · [paraphrase] M · [inferred] L`; exit-2 overwrite refusal.
- **plan** — `Spec dependencies set:`; frozen AskUserQuestion option strings (`proceed | mark-ready-then-proceed | abort`); autonomous-marker family.
- **prospect** — rejection-taxonomy slugs (`duplicates-open-epic | out-of-scope | out-of-scope-vs-strategy | insufficient-signal | too-large | backward-incompat | other`); option strings (`regenerate | loosen-floor | ship-anyway`, `keep | drop`) — "R19 anchor, must match across backends."
- **qa** — `qa_verdict` receipt; `SHIP/NA/BLOCKED/NEEDS_WORK` tokens; `P0/P1/P2` taxonomy.
- **interview / audit / make-pr / strategy** — their own receipt/section headers and any option strings; confirm per skill before trimming near them.

## Edge Cases & Constraints

- A skill whose baseline is already at ceiling (capture was 15/15) gets trim-that-holds experiments only — no invented quality levers for their own sake ("where it makes sense" = diagnosed blind spot, not decoration).
- Suites bootstrapped from history must SCRUB anything private and freeze inputs (copies, not live refs) so re-runs are stable — scrub is acceptance-gated per task (Major-5).
- Code-aware skills (plan, qa, interview-technical) carry ≥1 non-flow-next fixture to guard against overfitting trims to this repo (Major-2).
- Model constancy: all runs of one suite use the same model tier; record it in `results.tsv.model` + the README.
- interview/capture/plan consume or produce USER-AUTHORITATIVE spec.md — every suite for them carries the override-respect eval (hand-edited spec preserved; refusal paths intact).
- Runs of write-happy skills execute in a throwaway worktree/temp repo — never against the live `.flow/` (Major-1).
- fn-83 does not overlap Tier A files (work/worker are Tier B). **(Status: fn-83 merged to main 2026-07-03 (PR #196) — its "baseline against merged main" caveat is moot. fn-82 merged (PR #193) — the capture/make-pr re-baseline requirement is valid, current main reflects the fn-82 folds.)**
- Time-box per skill: if a suite can't reach trustworthy binary evals within the task budget, STOP, log why, and reclassify that skill to fn-85's conservative track — never ship a weak-eval "ratchet".

## Acceptance Criteria

- **R1:** Every Tier-A skill has a committed suite at `optimization/<skill>/` with ≥2-3 accuracy evals; bootstrapped inputs are frozen, SCRUBBED copies from real history (code-aware skills also carry ≥1 non-flow-next fixture).
- **R2:** Baseline rows recorded before any mutation, per skill (capture/make-pr re-baselined on current main), using the extended auditable `results.tsv` schema.
- **R3:** Every kept mutation shows accuracy held/raised AND (tokens down OR quality up) — auditable directly from `results.tsv` columns; every discard is logged with the regression that killed it. Zero kept mutations with an accuracy drop (ratchet integrity — audit the tsv in the PR).
- **R4:** ≥1 quality-lever experiment attempted per skill (kept or honestly discarded), targeting a diagnosed blind spot, with an eval that SCORES that behavior; over-flag guard run for any finder-shaped lever.
- **R5:** Proximity/repetition/marker-freeze constraints respected (spot-checked in review; no relocated consuming-phase tables).
- **R6:** `agent_docs/optimization-log.md` rows for every experiment; `optimizing-skills.md` target map updated at the end (Tier A now done).
- **R7:** Net effect table in the PR body: per skill — always-loaded tokens before/after, accuracy score before/after, quality levers kept — sourced from the `results.tsv` columns.
- **R8:** Mirror regenerated once per landed task; smoke + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).
- **R9:** Any skill reclassified out (weak evals) is explicitly listed with rationale — silent scope-shrink forbidden.

## Boundaries

- Review skills (impl-review, plan-review, spec-completion-review) OUT — already optimized; their rubrics only change via the review-prompt harness.
- Tier B/C skills OUT (fn-85). Agent files OUT (already budgeted).
- No structural moves (that was fn-82) — this spec rewords in place.
- No new skills/commands/flags; no flowctl changes.
- Machine-parsed markers and receipt grammars frozen.

## Decision Context

Per-skill autoresearch chosen over a bulk rewrite because rewording live judgment prose is exactly the mutation class that silently degrades quality — the ratchet converts "we think it's fine" into "the eval held". History-bootstrapped suites chosen over hand-authored corpora after costing: the repo's own specs/tasks are realistic frozen inputs at near-zero authoring cost, and eval realism dominates suite value — tempered by the anti-overfit non-flow-next fixture for code-aware skills (Major-2). The explicit quality agenda (blind-spot levers) is the fn-74 lesson generalized: quality wins come from LEAN additions at diagnosed misses, and they compose with trims (both axes, same loop). The time-box + reclassify rule exists because a ratchet with weak evals is worse than no ratchet — it launders regressions as "passed"; the extended auditable `results.tsv` schema is what makes "the eval held" checkable rather than asserted.

### Execution note — harness dispatch constraint (important for whoever runs these tasks)

The baseline/experiment mechanic dispatches an **isolated child agent** that reads the skill's prose files as its operating instructions and runs the skill on a frozen input (optimizing-skills.md L60-72), following the external methodology in `~/repos/autoresearch-skill` (`SKILL.md` + `eval-guide.md` — `git pull` before a run). **Its permission model is per-target, NOT uniformly read-only** — see Harness isolation: write-happy skills get a write-capable child confined to a throwaway worktree; side-effect-free run-tricks and `qa` get an output-only/read-only child. The `/flow-next:work` **worker agent has no `Task` tool** — it cannot dispatch children. Run each per-skill task from a **dispatch-capable context** (the main thread, or a driver that can spawn `Task`), OR split so a single worker iteration only builds the suite + records scores produced by externally-run agents. Write-happy skills run inside a throwaway worktree (see Harness isolation). Eval runs happen in child contexts (only compact scores return), keeping the orchestrator lean. The time-box + reclassify rule is the escape valve if a skill's loop can't converge within one iteration.

### Related specs (no dependency edges added)

- **fn-54** — ancestor umbrella; its R5/R6 are almost exactly this Tier-A list. fn-84 (+fn-85) is the direct continuation that closes it out — reverse dependency (fn-54 stays open until fn-84/fn-85 land). No edge to add.
- **fn-85** — companion Tier B/C, no skill-file overlap, but both write `agent_docs/optimizing-skills.md` (target map) + `optimization-log.md` — sequence the shared-file writes if the two ever run in parallel.
- **fn-73** — unplanned make-pr forge-abstraction work; would collide on `make-pr` skill files. Check its status before starting the make-pr task if it has since been planned.

## Early proof point

Task **fn-84.1 (`plan`)** validates the whole per-skill loop shape end-to-end on a NEW-from-history suite — INCLUDING the two riskiest mechanics this spec introduces: (a) the throwaway-worktree run isolation (Major-1) and (b) the non-flow-next anti-overfit fixture (Major-2). Bootstrap frozen inputs (flow-next + ≥1 non-flow-next) → author ≥2-3 accuracy evals (incl. the spec.md override-respect eval) → record baseline row 0 in the extended schema → run ≥1 trim + ≥1 quality lever (target plan's known task-ordering blind spot, with a scoring eval) → ratchet + log. If this loop cannot reach trustworthy binary evals within one iteration, STOP and re-evaluate the suite-bootstrap + isolation approach BEFORE fanning out fn-84.2–.8 — that is exactly the "reclassify to fn-85" escape. capture/make-pr (.2/.4) exercise the cheaper re-baseline path and are lower-risk.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Committed suite per skill, ≥2-3 accuracy evals, frozen+scrubbed history inputs (+non-flow-next fixture for code-aware) | fn-84.1–.8 | — |
| R2  | Baseline rows (extended schema) before any mutation (capture/make-pr re-baselined) | fn-84.1–.8 | — |
| R3  | Kept mutations hold/raise accuracy AND tokens↓/quality↑, auditable from results.tsv; discards logged; zero accuracy-drop keeps | fn-84.1–.8 (per skill) + fn-84.9 (final tsv audit) | — |
| R4  | ≥1 quality lever per skill WITH a scoring eval; over-flag guard for finder levers | fn-84.1–.8 | — |
| R5  | Proximity/repetition/marker-freeze respected | fn-84.1–.8 (evals assert frozen grammars) + fn-84.9 (spot-check) | — |
| R6  | optimization-log rows per experiment; target map updated at end | fn-84.1–.8 (rows) + fn-84.9 (target map) | — |
| R7  | Net-effect table in PR body (tokens + accuracy + levers per skill), sourced from results.tsv | fn-84.9 (consolidates; rendered at make-pr) | — |
| R8  | Mirror regen per task; smoke + pytest green; CHANGELOG Unreleased; no bump | fn-84.1–.8 (per task) + fn-84.9 (final gate) | — |
| R9  | Reclassified-out skills listed with rationale | fn-84.9 | — |

## Task breakdown (one loop per skill + consolidation)

Frequency-weighted, per the Architecture ordering. fn-84.1 (`plan`) is the proof point; fn-84.2–.8 depend on it (loop shape proven once) and are otherwise independent for their LOCAL work; fn-84.9 depends on all.

1. **fn-84.1 `plan`** — new suite (proof point: worktree isolation + non-flow-next fixture)
2. **fn-84.2 `capture`** — re-baseline existing suite (migrate to extended schema) + one mutation
3. **fn-84.3 `interview`** — new suite
4. **fn-84.4 `make-pr`** — re-baseline existing suite (migrate schema) + one mutation (add Where-to-look scoring eval first)
5. **fn-84.5 `audit`** — new suite
6. **fn-84.6 `prospect`** — new suite
7. **fn-84.7 `qa`** — new suite (scenario-derivation + bug-filing prose; non-flow-next fixture)
8. **fn-84.8 `strategy`** — new suite (smallest target)
9. **fn-84.9 consolidation** — final target-map update, ratchet-integrity audit (extended schema), reclassification list (R9), net-effect table (R7), CHANGELOG polish, authoritative sync-codex regen on merged main

### Shared-file discipline (Minor-6)

Each per-skill task OWNS only its local files: `optimization/<skill>/**` + `plugins/flow-next/skills/flow-next-<skill>/**`. These are disjoint across skills → the local suite/prose work parallelizes freely.

Three surfaces are SHARED and must NOT be treated as parallel-safe: `agent_docs/optimization-log.md`, `CHANGELOG.md` (`## Unreleased`), and `plugins/flow-next/codex/**`. They are append-only / generated: on parallel branches expect trivial append conflicts resolved at merge; `codex/**` is regenerated deterministically (re-run `sync-codex.sh` on merged main). Each task still appends its own log rows + CHANGELOG line + regens the mirror for its own PR (R6/R8); **fn-84.9 is the authoritative reconciler** — it verifies optimization-log completeness, finalizes the CHANGELOG, audits every `results.tsv`, and does the final mirror regen on merged main.

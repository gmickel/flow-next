# fn-83 Work-loop speed: conservative plan-sync gate + worker anchor bundle (zero quality loss, eval-proven)

## Overview

`/flow-next:work`'s wall-clock is dominated by serial machinery around the worker, not by the re-anchor. Measured (fn-81/fn-82 runs, 2026-07-02): plan-sync spawned unconditionally after every task returned "no drift" **3/3 times** at ~70-90k tokens and minutes each; the worker assembles its anchor through many separate reads. Fix: (a) a deterministic probe that PROVES no drift is possible before the plan-sync agent is spawned, (b) one `flowctl anchor` call delivering the same anchor information in one round-trip.

**Hard constraint (user-set): ZERO quality loss, PROVEN by an eval set before ship.** Re-anchoring is a core tenet — the bundle never reduces what the worker knows; the gate never skips a plan-sync that could have found drift. Both changes ship only behind their eval proof (`agent_docs/optimizing-skills.md` methodology; the fn-74 real-backend-in-the-loop pattern, `optimization/review-prompt/` is the template). **Precise claim scope:** the proof establishes zero false skips against the frozen real-agent oracle ON LATTICE INPUTS (paths, tokens, a truthful deviation flag). The two flag-dependent residual classes (deviation-only drift, plain-word symbol rename with an untruthful `PLAN_DEVIATION: no`) are closed by three mechanisms shipping together: (1) an explicit worker deviation RUBRIC (see Wiring) making the flag reliable by construction, (2) a RAMPED audit (1-in-2 for a repo's first 20 skips, then 1-in-5 — deterministic, ledger-derived) bounding first-miss exposure during the period the flag is unproven on that repo, (3) the append-only miss loop. Residuals are stated verbatim in the PR — never silent.

Deferred to a future spec: parallel disjoint-task execution, review pipelining.

## Quick commands

```bash
python3 -m pytest plugins/flow-next/tests/ -q               # incl. new lattice-arm + config + superset tests
(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)
bash scripts/sync-codex.sh                                   # worker/phases edits mirror; flowctl shared
python3 plugins/flow-next/tests/run_gate_corpus_check.py     # probe vs FROZEN answer key (exact name at impl)
```

## Approach

**1. Probe (`flowctl plan-sync-probe <task-id> --json`) — pure deterministic Python.**

- **Touched-set (RANGE-BASED — evidence completeness is load-bearing):** the worker today records only HEAD as its evidence commit, but review-fix loops create multiple commits per task — per-commit enumeration of an incomplete list would miss earlier drift-relevant changes. So: (1) the worker captures `BASE_COMMIT` (rev-parse HEAD at Phase-1 end, before any edit) and `flowctl done` evidence gains an additive `base_commit` field plus the full commit list (`git rev-list --reverse <base>..HEAD`); (2) the probe computes the touched-set from ONE RANGE DIFF `git diff --no-renames --name-status <base_commit> <head_commit>` (NEVER `--name-only`, it drops old rename paths; `--no-renames` renders renames as D+A so both paths count; interleaved foreign commits only over-approximate — safe direction), and hunk tokens from `git diff <base>..<head>` unified output; (3) **evidence without `base_commit` (older tasks, foreign writers, empty/missing evidence) ⇒ `spawn`** — completeness is proven or the gate does not apply. Evidence read from runtime state via `load_task_with_state` (flowctl.py:959-979 area; written at cmd_done flowctl.py:16476) — NOT parsed from task markdown.
- **Downstream reference extraction** (net-new; no parser exists today): from every downstream todo task's body — and, when `planSync.crossSpec=true`, ALSO every open spec's BODY (plan-sync Phase 4b scans spec bodies, not just tasks) — extract path-shaped references — `**Files:**` entries, `## Investigation targets` paths, any path-like token in prose (backtick-tolerant, `path:12-40`-suffix-tolerant, relative/absolute). Compare via `PurePosixPath` (git paths are always `/`), exact + basename + directory-prefix matches all count; Python 3.8-safe (`parts`-tuple prefix compare, NOT `is_relative_to` — 3.9+).
- **Symbol-token arm (required for recall — git renames are heuristic and symbol renames move NO path):** tokenize the `+`/`-` hunk lines of the base..head range diff (both sides — old names live on `-`) and keep tokens passing a MORPHOLOGICAL identifier predicate (contains `_`, camelCase hump, dotted/`::`/`->` compound, ALL_CAPS≥2, or contains a digit — shape-based, deterministic, NO English stoplist per repo doctrine); any kept token appearing word-bounded in a downstream body ⇒ overlap. Plain-single-word symbols (e.g. `parse`→`read`) deliberately fail the predicate — that class is covered by the deviation flag + audit sampling and is part of the stated residual.
- **Deviation fact:** worker's mandatory terminal `PLAN_DEVIATION: yes|no` (parsed by anchored prefix regex over the whole return, last match wins — NOT positional; missing/malformed ⇒ `yes`; worker.md instructs "unsure ⇒ yes"). Emission slot: immediately before the DELEGATION lines; all three host parses are prefix-anchored (fixes the last-two-lines fragility while keeping order readable).
- **Decision lattice (fail-open):** `skip` ONLY when: no path overlap AND no token overlap AND `PLAN_DEVIATION: no` AND probe ran clean AND every scanned body (downstream task; plus each open spec body under crossSpec) yielded ≥1 parseable reference (any body with none ⇒ cannot prove disjoint ⇒ spawn) AND evidence carries `base_commit` (range provably complete) AND (crossSpec off OR cross-spec enumeration succeeded). Anything else ⇒ `spawn`. No pipelines in probe internals (rc-checked subprocess calls).
- **Gate ledger:** `plan-sync-probe --record <mode>` appends to `.flow/plansync-gate.jsonl` (atomic append) with the FIXED schema `{ts, spec, task, mode, decision, skip_index, audit_spawned, actual_drift: yes|no|null, audit_miss: bool, reason}` — the durable store pairing shadow/audit would-decisions with actual `Drift detected:` verdicts; `skip_index` drives the deterministic audit ramp.

**2. Config.** `planSync.gate = off | shadow | on` added to the existing materialized `planSync` block (get_default_config, flowctl.py:1185). Matrix: `planSync.enabled=false` ⇒ 3e skipped entirely (today's rule, gate irrelevant). `enabled=true`: `off` ⇒ always spawn (probe not invoked); `shadow` ⇒ probe + record would-decision + ALWAYS spawn (behavior byte-equivalent to today); `on` ⇒ probe-gated with **ramped audit sampling**: deterministic ledger-derived counter — every 2nd skip spawns plan-sync anyway for the repo's first 20 skips, every 5th thereafter — records the pairing; an audit spawn whose verdict is `Drift detected: yes` is an **AUDIT MISS** — surfaced loudly in the run summary + ledger and instructs flipping to `shadow`; the system NEVER mutates the user's config itself. Default **`on`** (justified by the in-PR proof; `shadow` documented as the cautious adoption path).

**3. Ground-truth eval harness (`optimization/plan-sync-gate/`) — the merge gate.**

- **Corpus:** ≥10 constructed drift-POSITIVE scenarios — API/symbol rename consumed downstream (morphological and plain-word variants), deviation-only drift (zero file overlap), acceptance-semantics staleness, file rename/move listed downstream, cross-spec drift, prose-only shared-contract reference — plus ≥10 drift-NEGATIVE scenarios replayed from real history (fn-81/fn-82 post-task states via `git worktree add --detach <full-SHA>`; task ids are slug-form on disk; husk inputs reconstructed AT the pinned SHA). Corpus is **append-only**; every future live miss becomes a permanent scenario.
- **Answer key (generated once, then FROZEN):** run the REAL production `agents/plan-sync.md` (its own `model: opus` pin = the held-constant model; record resolved model id) with its full input contract (COMPLETED_TASK_ID, SPEC_ID, FLOWCTL, DOWNSTREAM_TASK_IDS, `DRY_RUN=true`, CROSS_SPEC, at-SHA GLOSSARY_JSON/DECISIONS_JSON/STRATEGY_CONTENT husks) — N=3 runs per scenario, majority vote; ANY flip across runs ⇒ classified drift-positive (wobble = ambiguity = drift; NeurIPS-2025-backed). The parsed `Drift detected: yes|no` P6 line (plan-sync.md:240-288) is the label. Key committed; **CI validates the deterministic probe against the frozen key — the LLM is never re-run in CI.**
- **Adversarial flag arm:** every drift-positive scenario ALSO probed with `PLAN_DEVIATION=no` forced — the probe must still `spawn` on its path/token arms for every scenario whose drift is path/token-visible. The two classes where flag=no defeats the probe (deviation-only drift, plain-word symbol rename) are the **stated residual**: today they're caught only because plan-sync always runs; under `on` they're caught by (a) the worker flag (instructed unsure⇒yes, missing⇒yes), (b) 1-in-5 audit sampling, (c) the append-only miss loop. This residual is documented in the PR verbatim — the proof claims zero false skips ON THE LATTICE'S INPUTS, plus bounded-and-instrumented residual on untruthful inputs.
- **Merge gates + honesty:** false-skip count == 0 across the corpus (hard); rule-of-three bound stated explicitly (0 FN in N ⇒ FN-rate ≤3/N @95% — at N=20 that is ≤15%; the audit loop is the ongoing tightener); skip-rate on drift-negatives reported (target ≥80%; <50% ⇒ ship-with-rationale decision point since the gate's complexity must pay).

**4. Anchor bundle (`flowctl anchor <task-id> --json|--md`).** Clone/refactor `cmd_spec_export_cognitive_aid`'s section assembly (flowctl.py:14845-15025) + fn-79 fence-aware helpers. Contents — the VERBATIM RAW OUTPUTS of every command worker.md Phase 1 currently runs: `show <TASK_ID> --json`, `cat <TASK_ID>`, `show <SPEC_ID> --json`, `cat <SPEC_ID>` (FULL spec body — no R-ID filtering), `git status` + `git log -5 --oneline` + branch, `config get memory.enabled`, `glossary list --json`, `memory list` index when memory enabled — plus dependency tasks' ids/titles/done-summaries. The superset test compares against these exact command outputs, not paraphrases. Verbatim sections, no summarization, no truncation. **Worker-invoked at its Phase 1** (same point-in-time semantics as today's reads — never host-precomputed, so it observes the prior task's plan-sync edits). Worker retains memory keyword-SEARCH and all read-more freedom (bundle is a floor).

- **Superset test:** deterministic — every artifact worker.md Phase 1 currently reads (worker.md:21-68: show/cat task+spec, git status/log, memory.enabled, glossary list, memory list) present verbatim in the bundle on fixture data.
- **Comprehension-equivalence eval (`optimization/worker-anchor/`):** ≥3 frozen real tasks; K binary questions graded against a committed ANSWER KEY (not bundle-vs-statusquo agreement — both-wrong must fail); ≥1 question answerable ONLY from a non-`satisfies` spec section (guards any future filtering regression); grading model fixed and recorded. Bundle score ≥ status-quo score AND ≥ key threshold on every set.

**5. Wiring.** phases.md 3e: gate branch (mode matrix, probe call, audit counter, per-task `plan-sync:` summary slot in ALL modes — `spawned (reason) | skipped (proof) | shadow: would-… | audit: …`), and **fix the latent CROSS_SPEC bug** (spawn prompt at phases.md:379-388 omits `CROSS_SPEC` though plan-sync.md:19 documents it — pass it from `planSync.crossSpec`). worker.md: PLAN_DEVIATION line with an explicit RUBRIC — emit `yes` when ANY of: API/function/name change beyond the task spec; contract/schema/shape change; file set differs from the task's Files list; scope grew/shrank; an AC was satisfied differently than specified; dependency assumptions changed; glossary/strategy-relevant wording introduced; test plan diverged; ANY uncertainty ⇒ `yes` — plus single anchor call + floor-not-ceiling prose; a prose regression test asserts the rubric + line grammar survive edits and the mirror. Probe/anchor argparse registration follows the prospect subparser shape (flowctl.py:25991-26019).

## Boundaries / non-goals

- NO parallel task execution, NO review pipelining, NO review-backend changes.
- NO changes to plan-sync's own prompt/judgment (fn-85 Tier B owns that; the CROSS_SPEC wiring fix is caller-side).
- NO summarizing/filtering of anchor content; NO English stoplists (morphological predicate only).
- The gate never ships without the zero-false-skip proof; if the corpus defeats the probe, the outcome is "gate not shippable, evidence attached" — never a weakened corpus.
- The system never mutates `planSync.gate` itself (audit miss surfaces + instructs; the flip is the user's).
- flowctl stays pure-stdlib Python 3.8+.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — per-task loop cost drops (the 3/3 wasted plan-syncs were autonomous-run overhead); gate rides receipts, never prompts; audit sampling keeps autonomous quality observable.
- **Self-improving through normal work** — the gate ledger + append-only corpus turn live operation into eval fuel; harnesses extend the optimization/ methodology surface.
- **Cross-platform parity** — worker/phases edits mirror via sync-codex; flowctl is shared; Windows-safe path handling (PurePosixPath, 3.8-safe) per fn-77 discipline.

## Decision context

- User rejected shadow-first ("prove there is no quality loss with an eval set") — the harness is the centerpiece and merge gate; default `on` is justified by the in-PR proof, with `shadow` as the documented cautious path.
- Symbol-token arm added after research: git rename detection is heuristic and symbol renames move no path — path-intersection alone cannot reach recall-1. Morphological predicate (shape-based) chosen over frequency/stoplist filtering to honor repo doctrine; the plain-word gap is consciously routed to flag+audit rather than a stoplist.
- Answer-key-frozen design (LLM labels generated once, CI deterministic forever) copies the review-prompt harness; wobble⇒positive is principled under rating indeterminacy (arXiv:2503.05965).
- Full-spec bundle (no filtering) resolves the superset contradiction the gap analysis caught; the bundle's win is round-trips, not content reduction.
- Audit sampling is deterministic 1-in-5 (counter, not RNG — flowctl determinism doctrine); config never auto-mutated (autonomous safety: a self-flipping config mid-Ralph-run is worse than a loud miss).
- Union-of-per-commit-diffs over first^..last range: avoids sweeping unrelated interleaved commits into the touched-set.
- Residual honesty: the zero-false-skip claim is scoped to lattice inputs; deviation-only drift with an untruthful flag is the named residual, bounded by unsure⇒yes instruction + audit loop + append-only corpus. Stated in the PR, not buried.

## Acceptance Criteria

- **R1:** `flowctl plan-sync-probe` implements the fail-open lattice (paths + morphological tokens + deviation + clean-run + parseable-refs + base-commit-present + cross-spec arms); pure stdlib, 3.8-safe, PurePosixPath, `--no-renames --name-status`, RANGE diff base..head, no pipelines; unit tests cover EVERY lattice arm both ways including multi-commit fix-loop tasks and missing-base fail-open.
- **R2:** `optimization/plan-sync-gate/` committed: ≥10 constructed drift-positive + ≥10 history-replayed drift-negative scenarios (worktree --detach, full SHAs, at-SHA husks, slug-form ids), append-only README rule, adversarial PLAN_DEVIATION=no arm.
- **R3:** FROZEN answer key generated from the REAL plan-sync agent (DRY_RUN, full input contract, N=3 majority, wobble⇒positive, model id recorded); CI check validates probe vs key with **zero false skips** (hard merge gate) and never re-runs the LLM; `.github/workflows` path filters extended to cover `optimization/plan-sync-gate/**` + `optimization/worker-anchor/**` so corpus/key changes always trigger the check.
- **R4:** Rule-of-three bound and skip-rate reported (target ≥80% on drift-negatives; <50% triggers a documented ship-with-rationale decision); the deviation-only/plain-word residual stated verbatim in the PR.
- **R5:** Worker records `base_commit` + the full base..HEAD commit list in `flowctl done` evidence (additive schema field; multi-commit fix-loop tasks fully covered), and emits `PLAN_DEVIATION: yes|no` governed by the explicit yes-trigger RUBRIC (API/name/contract/files/scope/AC-coverage/dependency/glossary/strategy/test-plan deviations; unsure⇒yes; missing/malformed⇒yes); prefix-anchored parse, last-match-wins; DELEGATION-line parsing prose updated to prefix-anchored alongside; prose regression test covers rubric + grammar + mirror.
- **R6:** `planSync.gate` config (off|shadow|on, default on) with the enabled×gate matrix documented; config tests per the pipeline-qa string-enum pattern; shadow mode byte-equivalent behavior + ledger records; gate ledger `.flow/plansync-gate.jsonl` written in shadow/on modes.
- **R7:** Ramped audit sampling in `on` mode: deterministic ledger-derived 1-in-2 for the repo's first 20 skips, 1-in-5 thereafter; AUDIT MISS surfaced in summary + ledger with flip-to-shadow instruction; config never auto-mutated; Ralph path receipt-visible, never prompting.
- **R8:** `flowctl anchor` implemented (full spec body, no filtering; verbatim; worker-invoked); deterministic superset test green against worker.md Phase 1's current read list.
- **R9:** Comprehension-equivalence eval green: answer-key-graded, ≥3 frozen tasks, non-satisfies-section question included, bundle ≥ status-quo AND ≥ key threshold; committed under `optimization/worker-anchor/`.
- **R10:** phases.md 3e gate wiring (mode matrix + summary slot in all modes + audit counter) and worker.md changes landed; **CROSS_SPEC now passed to plan-sync spawns** (latent-bug fix); mirror regenerated; smoke (non-repo cwd) + full pytest green.
- **R11:** Real multi-task work run on this repo with gate `on` shown in the PR (per-task `plan-sync:` slots + ledger excerpt); anchor round-trip count before/after.
- **R12:** Docs: flowctl.md (both commands per house style + `planSync.gate` config row with adoption note), architecture.md eval-proof paragraph, optimizing-skills.md harness pointers, GLOSSARY Re-anchoring/Worker touch-up, CHANGELOG under `## Unreleased` (create), docs-site same-workstream edits (work.mdx plan-sync section + mermaid node, configuration.mdx `planSync.gate` section sibling to crossSpec, subagents/execution.mdx + overview.mdx gate footnotes; `pnpm build` green; NO FLOW_NEXT_VERSION bump).
- **R13:** No version bump (batched); optimization-log.md rows for harness outcomes.

## Early proof point

Task fn-83.1 (probe) + fn-83.2 (harness) are the proof spine: if the corpus defeats the lattice (any false skip survives iteration), STOP — the gate is not shippable and the spec pivots to evidence-attached shelving; the anchor-bundle half (fn-83.3) is independent and proceeds regardless.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | probe + lattice + unit tests | fn-83.1 | — |
| —  | task ordering: .3 depends on .1 (same-file flowctl.py); .4 depends on .1+.2+.3 (wiring never lands before the proof) | deps recorded | — |
| R2  | corpus (pos+neg, adversarial arm) | fn-83.2 | — |
| R3  | frozen answer key + CI zero-false-skip | fn-83.2 | — |
| R4  | bounds + skip-rate + residual statement | fn-83.2 (measured), fn-83.5 (PR) | — |
| R5  | PLAN_DEVIATION line + parsing | fn-83.4 | — |
| R6  | gate config + ledger + shadow | fn-83.1 (flowctl), fn-83.4 (skill) | — |
| R7  | audit sampling + AUDIT MISS | fn-83.4 | — |
| R8  | anchor + superset test | fn-83.3 | — |
| R9  | comprehension eval | fn-83.3 | — |
| R10 | wiring + CROSS_SPEC fix + mirror + gates | fn-83.4 | — |
| R11 | live-run evidence + round-trip counts | fn-83.5 | — |
| R12 | repo docs + docs-site | fn-83.5 | — |
| R13 | no bump + optimization-log | fn-83.5 | — |

# Autoresearch — plan (fn-84.1, Tier A proof point)

Eval-driven optimization of `/flow-next:plan` (skill across `SKILL.md` + `steps.md` +
`examples.md`, ~10.2k prompt tokens). `plan` is a **repo-context, spec.md-authoritative,
task-decomposing** skill: it consumes research + a request (or an existing spec) and emits a
spec + tasks. The evals measure **judgment quality** — R-ID coverage, requirement coverage,
task sizing, override-respect, and dependency ordering — NOT "is plan's spec the one true spec."

Ratchet (correct hill-climb): `accuracy_score` is the zero-quality-loss floor — it must never drop;
keep iff `accuracy_score ≥ baseline` AND at least one improves (accuracy up, tokens down, or
`quality_score` up). Audited from `results.tsv` (fn-84 extended schema). Zero quality loss is the
binding constraint (fn-84 Goal). Suite has **4 frozen fixtures** (P1 flow-native, P2 non-flow-next,
P3 override-respect, P4 ordering/sizing stress) — max_score 20 (accuracy 16 + quality 4).

## Run-trick — frozen-research-bundle emission (the design decision)

`plan` has **no side-effect-free CLI mode** (capture = `mode:autofix`, make-pr = `--dry-run`;
`plan` writes specs/tasks to `.flow/` and orchestrates a scout fleet). fn-84's Harness-isolation
section prescribes a throwaway worktree for write-happy skills. For THIS suite we use the
methodology's established, more tractable and more deterministic mechanic (autoresearch
`eval-guide` + `optimizing-skills.md` L60-72 "Output ONLY the result"):

- Each run dispatches a read-only `general-purpose`/`Explore` subagent given the plan **prose
  files as its complete operating instructions** (baseline reads `baseline/{SKILL,steps,examples}.md`;
  experiments read the live `plugins/flow-next/skills/flow-next-plan/*.md`), plus a **frozen fixture**
  (request + frozen research bundle + P3's existing spec). It **emits the spec + tasks it would
  create** as markdown — it writes nothing to `.flow/` and dispatches no sub-scouts.
- **Why frozen research, not a live worktree run:** (1) it isolates the *judgment prose* fn-84.1
  optimizes — the scouts are already optimized (fn-54/82) and are non-deterministic (live web / `gh`),
  so freezing them is correct eval hygiene, exactly the methodology's "hold inputs constant"; (2) it
  is deterministic and cheap enough to run the full loop; (3) the plan skill's Step-1 fan-out is a
  separate optimization surface, out of scope for the prose-judgment measurement. The worktree+live
  ideal remains the escalation path if emission proves insufficient — it did not here.
- **Permission model:** output-only / read-only child (it emits, never writes) — no worktree needed
  for this mechanic. **Non-interactive:** the fixture supplies all context; the subagent is told not
  to ask (no `AskUserQuestion` reachable in a dispatched subagent anyway).

## Anti-overfit (fn-84 Major-2)

`plan` is code-aware, so P2 is a **non-flow-next** fixture (`~/work/DocIQ-Sphere`, a FastAPI/OOXML
DOCX backend) — a kept trim must judge well on foreign code, not just flow-next's own conventions.
P1 (flow-native) + P3 (existing flow-next spec, override-respect) round out the 3.

## Model constancy

All runs (baseline + every experiment) use **`sonnet`** — held constant so scores compare
apples-to-apples (the ratchet needs constancy, not a specific tier). Recorded in `results.tsv.model`.

## Files

`test-inputs.md` (3 frozen fixtures) · `evals.md` (5 binary: E1–E4 accuracy, E5 the quality-lever
scoring eval, all finalized before baseline) · `results.tsv` (extended schema) · `changelog.md`
(per-experiment log — resume from here) · `baseline/{SKILL,steps,examples}.md` (pre-mutation prose) ·
`holdout/{input,oracle,README}.md` (task-130.7 sealed P5; input and answer key are separated) ·
`task-130-7-results.tsv` (independent routing/examples keep ledger and reached-path pairs).

## Resume

Read `changelog.md` for what ran and why. `results.tsv` row 0 is the baseline (scored under the
final eval set). To re-run an experiment: reset the live prose to `baseline/`, apply the one
mutation, dispatch the 4 fixtures at `sonnet`, score against `evals.md`, append a row.

## Rigor notes (fable-review pass, addressed)

- **N / majority-vote.** N=1 per fixture, EXCEPT P4 (the borderline judgment cell) at **N=2** — baseline P4 E3=FAIL and exp1 P4 E3=PASS were BOTH confirmed on two runs, so the 15→16 gain is not N=1 noise. `results.tsv.runs` stays a clean integer (1); the per-fixture N is in each row's description.
- **`discard-HOLD` status** (results.tsv row 2) = *considered + deferred on a verifiability principle*, NOT run-and-reverted (which would be `discard-REVERT`). An extension of the `baseline|keep|discard-REVERT` set; noted here for fn-84.9's mechanical audit.
- **E3 contamination — next iteration needs a fresh sizing fixture.** The kept cue's ❌ example now verbatim-encodes P4's baseline over-split (docs+CI as two tasks), so P4-E3 is memorized for future runs. A future E3 experiment must use a NEW sizing fixture or a sealed holdout.
- **Task-130.7 sealed holdout.** P5 was frozen before its prompt candidate. It adds independent no-code, research-consumption, R-ID, cohesion/dependency, Mermaid, and optional-route cells. The subject sees only `holdout/input.md`; `holdout/oracle.md` stays scorer-only.
- **Frozen grammars are outside the emission surface.** The emission run-trick exercises only the authoring-judgment surface (Steps 2–5); plan's frozen grammars (`Spec dependencies set:`, AskUserQuestion option strings, autonomous markers) are NOT reachable by these runs, so R5's "grammar unchanged" is guarded at **diff review**, not by an eval. Only E1's R-ID grammar is eval-asserted.
- **Keep-rule (for fn-84.9's cross-suite audit).** This suite uses the corrected hill-climb: accuracy_score is the floor (never drops); keep iff accuracy_score ≥ baseline AND at least one of {accuracy↑, tokens↓, quality↑}. This admits an accuracy-up-at-token-cost keep (matches the spec's own fn-74 exemplar: +74 tok for 8.0→9.3). fn-84.9 must adopt ONE canonical keep-rule across suites.
- **Worktree-isolation mechanic DEFERRED.** fn-84.1 (as proof point) used output-only emission, NOT the throwaway-worktree write mechanic (Major-1/C). The worktree mechanic therefore stays **unproven** — the first write-happy suite to exercise it (**fn-84.3 interview** or **fn-84.5 audit**) must prove it before relying on it.

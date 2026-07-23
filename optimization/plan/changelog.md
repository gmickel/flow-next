# Changelog — plan suite (fn-84.1)

Per-experiment log. Resume from the latest experiment. Model `sonnet`, 4 frozen fixtures
(P1 flow-native, P2 non-flow-next/DocIQ-Sphere, P3 override-respect, P4 ordering/sizing stress),
N=1 per fixture. Eval set: E1–E4 accuracy, E5 quality (ordering); ratchet = accuracy never drops,
keep iff something improves (accuracy up / tokens down / quality up).

---

## Experiment 0 — baseline (status: baseline) — accuracy 15/16, quality 4/4, ~10,176 prompt tokens

Ran the original prose (`baseline/{SKILL,steps,examples}.md`) on all 4 fixtures.

- **P1** (flowctl specs --unsynced, flow-native): 5/5. R1–R7 tagged; coverage table complete; 2 tasks (M+S); `.2 depends_on .1`. Clean.
- **P2** (DocIQ-Sphere rate limiting, NON-flow-next): 5/5. R1–R8; 3 tasks; tests+docs both `depends_on .1`. **Grounded in foreign code** — cites FastAPI/`/api/*`/`commit_batch`/`/scalar`/token-bucket/429, not flow-next patterns → anti-overfit held.
- **P3** (fn-88 existing hand-edited spec, override-respect): 5/5. **R1/R2/R4/R7 preserved, gap not compacted; hand-edited no-compression boundary kept verbatim** — E4 (Major-4 guard) intact.
- **P4** (flowctl doctor, ordering/sizing stress): **4/5 — E3 FAIL.** 6 tasks; the DAG is *correct* (E5 PASS: `.1` registry is the foundational no-dep proof-point task, checks `.2/.3` depend on `.1` not each other, `--fix .4 depends_on .2` the check it repairs). But it **over-split**: `.5 docs+CHANGELOG` and `.6 CI-wiring` are two trivial sequential S tasks that should be ONE (CI-wiring belongs to the test/docs task's DoD). The prose's combine rule only triggers at "7+ tasks" — a 6-task over-split slips under it.

**Key finding (drives the experiments):** the a-priori quality lever (dependency-ordering / P6) has
**NO headroom** — E5 is 4/4 at ceiling, ordering is correct even on the stress fixture. The REAL,
data-diagnosed blind spot is **task sizing/combining (E3)**: over-splitting trivial finalization
tasks below the 7-task combine trigger. So:
- **Exp 1 = quality lever pivoted to E3** — a lean "finalization/sequential-S tasks fold" cue at the task-sizing phase (its scoring eval E3 is pre-authored → Major-B-clean).
- **Exp 2 = a prose trim** that must hold accuracy while cutting tokens.

---

## Experiment 1 — quality lever: finalization-fold cue (status: KEEP) — accuracy 15→16, quality 4/4, +117 tok

**Hypothesis (from exp 0):** the real blind spot is E3 (sizing/combine), not E5 (ordering). Baseline
over-split P4 into 6 tasks with `docs` + `CI-wiring` as separate trivial S tasks; the prose's combine
rule only triggers at "7+ tasks".

**Mutation (LEAN, at the consuming phase — proximity):** +6 lines at `steps.md` Task Sizing Rule:
"7+ is a ceiling, not a floor — combine trivial sequential S tasks even below it; **finalization folds
into ONE task** (docs + CHANGELOG + release-notes + CI/test-wiring); CI-wiring is a task's DoD, not its
own task."

**Result (4 fixtures, N=1; P4 confirmed N=2):**
- **P4** E3 fail→PASS on BOTH runs — `flowctl doctor` now emits 5 tasks with ONE combined
  `docs+CHANGELOG+CI` finalization task (was 6 with `.5 docs` + `.6 CI` split).
- **P1/P2** also fold finalization into one task (`"Docs + CHANGELOG + CI wiring"`), no regression.
- **P3** override still preserved (R-IDs, hand-edited boundary intact).
- accuracy **15→16**, quality held 4/4, tokens +117.

**Ratchet:** accuracy rose, nothing regressed → **KEPT**. A correctness/quality win for +117 tok — a
lean targeted block at a diagnosed miss (the fn-74 lesson, generalized). Note the **pivot**: the a-priori
lever (dependency-ordering, E5) had NO headroom (ordering was already correct on all 4 incl. the stress
fixture); the baseline data redirected the lever to the E3 gap. Both are pre-authored evals → Major-B clean.

---

## Experiment 2 — prompt trim (status: DISCARD-HOLD, principled) — no change kept

**Hypothesis:** compact `examples.md`'s two verbose BAD full-code example blocks (~500 tok) — the code
dumps shown only to illustrate "don't write implementation code."

**DISCARDED — not on a regression, on a verifiability principle (the stronger form of zero-quality-loss):**
1. The trimmed blocks govern the Golden-Rule **"no implementation code in the emitted spec"** behavior —
   which **no eval in this suite scores** (E1–E5 cover R-IDs / coverage / sizing / override / ordering).
2. Structurally, the emission run-trick only exercises the **authoring-judgment surface** (Steps 2–5).
   A trim to ANY prose outside that surface (Step 1 research, Step 7 review, mermaid/investigation examples,
   the no-code BAD blocks) would score **16/16 trivially** — the path is never exercised, so the "hold" is
   false. Keeping it would be the exact **"ratchet worse than none"** failure fn-84's Decision Context warns
   against.
3. The only trims THIS suite can validly ratchet are to the authoring-judgment prose itself — which is
   load-bearing (proximity; capture's analogous DRY trim regressed 15→14). No safe headroom there.

**Finding (suite-quality, the real value of this discard):** the plan suite needs a broader eval surface
before trims can be ratcheted — an **E6 "no implementation code in emitted spec/tasks"** eval, plus coverage
of the research/mermaid/investigation paths. Adding evals forces a fresh baseline (Major-B), so the trim is
**real headroom gated behind an eval-suite expansion**, logged for the next iteration — not a fake keep.

## Net result

**1 kept (quality: accuracy 15→16, +117 tok) · 1 honestly discarded (trim, unverifiable → deferred).**
Zero accuracy loss. The kept mutation is live in `plugins/flow-next/skills/flow-next-plan/steps.md`.

---

## Task 130.7 pre-candidate freeze — V1/B1 + sealed P5

Before mutating `examples.md` or optional routing prose:

- `python3 optimization/reached-path/run_eval.py --validate-b1` passed for all
  117 manifests.
- `python3 optimization/reached-path/run_eval.py --check-b1-input plan` passed
  for all four Plan prompt files.
- P5 was frozen under `holdout/`: a non-flow-next no-code architecture request,
  a fixed research bundle, R1–R6, a Mermaid condition, and tracker/HTML/review
  on/off inputs. Its H1–H10 scorer lives in a separate file not visible to the
  subject.
- B1 deterministic router evidence is 50,243 reached-path characters. Backend
  telemetry is explicitly unavailable in this Codex-session-only worker run
  and is not inferred from source bytes or wall time.

This freeze is the new baseline for the previously held examples trim. P4 is
still contaminated and cannot make the keep decision by itself.

## Task 130.7 candidate — KEEP routing and examples independently

Two independent mutations were compared only to hash-verified V1/B1:

1. **Optional routing — KEEP.** Step 6.5 retains the existing tracker
   active+leaf probe; Step 7 uses the already selected review mode; Step 8.5
   retains the existing HTML value from the single Step 0 snapshot. Only after
   a signal is on does Plan load its one-level direct reference. Default
   authoring falls 6,149 characters (10.01%); selected paths also improve:
   tracker 10.71%, review 10.59%, HTML 4.57%.
2. **Examples trim — KEEP.** The two BAD full implementation dumps became
   short anti-pattern anchors. The Golden Rule, forbidden/allowed lists, both
   GOOD examples, research/investigation, sizing/cohesion/dependency, R-ID, and
   Mermaid guidance remain. Independently saves 957 characters (1.56%) on the
   authoring path.

The combined default authoring path is 61,420 → 54,314 characters (-7,106,
11.57%). Deterministic pairs were repeated N=2 and matched exactly.
`test_skill_prose_diet` pins gate-before-read ordering, cold details, one-level
references, short BAD anchors, and holdout answer-key separation. The H1–H10
contract audit is zero-loss; backend/model telemetry is `null` because this
worker was constrained to the current Codex session. No token, cache, quality,
or wall-time claim is inferred from deterministic characters.

---

## Review pass (fable, our review rules) — verdict SHIP; rigor fixes applied

Fable-model adversarial review confirmed the ratchet is honest (the a-priori E5 lever was invalidated
by the data and reported as such — the strongest anti-gaming signal) and the trim discard is principled.
Applied its actionable findings:
- **[MEDIUM] baseline P4 N=1 asymmetry** — re-ran baseline P4 (N=2): **E3 FAIL reproduced** (again split
  `.5 tests+CI` + `.6 docs+CHANGELOG` into two finalization tasks). The 15→16 gain is confirmed real, not
  noise. Recorded in `results.tsv` row-0 description.
- **[MINOR] ledger** — true N documented per fixture; `discard-HOLD` status explained in README.
- **[MINOR] Major-B evidence** — moved the pivot narrative out of the "frozen" `evals.md` into this
  changelog; `evals.md` now states only the stable eval set.
- **[MINOR] E3 contamination + frozen-grammar/worktree gaps** — documented in README § Rigor notes
  (fresh sizing fixture next iteration; frozen grammars guarded at review; worktree mechanic deferred to
  the first write-happy suite).
- **[NIT]** removed the empty `fixtures/` dir (frozen inputs live in `test-inputs.md`).

Deviations from the task's literal approach, disclosed: fixtures P1/P4 are invented-realistic (not verbatim
"drawn from real spec Goal sections") — privacy-friendlier, same eval value; P3's synthetic id `fn-88` may
cosmetically collide with a future real fn-88 (harmless — it's a frozen fixture, never written to `.flow/`).

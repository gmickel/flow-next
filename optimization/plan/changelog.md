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

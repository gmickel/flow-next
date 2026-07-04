# Changelog — interview suite (fn-84.3)

Model `sonnet` (runs); `fable` independent judge for E4/E5 (question quality). 4 fixtures
(I1 thin flow-native, I2 non-flow-next DocIQ, I3 override-respect, I4 restraint-stress).
Run-trick: question emission (README). Ratchet: accuracy (E1–E3) never drops; keep iff
accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑) — audited from `results.tsv`.

## Experiment 0 — baseline — accuracy 12/12, quality 7/8, ~12,314 tok
- **E1–E3 (host) 12/12:** all 4 held — no codebase-answerable re-asks, format contract (lead-rec +
  confidence tier, honest `[your-call]`), I3 preserved BOTH DECIDED boundaries + the R-ID gap.
- **E4–E5 (fable) 7/8:** I1/I2/I3 E4+E5 PASS (I2 foreign-code grounded; strong NFR coverage +
  question quality). **I4 E5 FAIL** — over-asked a thorough spec (5 Qs incl. a `[high]`-confidence
  one it would just accept + a self-admitted-taste one; expected 0–2). **Diagnosed blind spot:
  interview over-asks on well-specified specs** (its own "expect 40+ questions" bias).
- **NOISE FINDING (from the later N=2 re-run):** baseline I3 is NOISY — a second run scored E4+E5
  FAIL (3/5) where the first scored 5/5. The 7/8 is a lucky single run; true baseline ≈ 6.5/8. E5
  ("is this padding") is a ~50%-flip subjective judgment on the hard fixtures.

## Experiment 1 — quality lever (restraint / prune) — DISCARD-REVERT
**Mutation (LEAN +6 lines, at the consuming phase — SKILL.md Question Order):** "match question count
to spec completeness; the 40+ is not a target; prune before asking — (a) a `[high]`-confidence question
you'd just accept → record as a resolved assumption, don't ask; (b) a pure-taste question → decide, don't
ask; state what you're NOT asking and why."

**Result — the lever WORKS on its target, but the ratchet can't confirm a net win:**
- **I4 (target): E5 FAIL → PASS.** 5 padding questions → 3 sharp ones + explicit declines; it even
  surfaced a genuine R2-vs-R4 spec contradiction baseline missed. On the nose.
- **I3: E4 noisy → SOLID** (PASS both N=2 lever runs vs baseline's coin-flip); consistently shorter
  (9–11 Qs vs baseline 12–14, which even invented scope-creep fields `schema_version`/`actor`), richer
  "not-asking" declines.
- **I2: held.** **I1: REGRESSED qualitatively** — on the *thin* fixture the prune cue **dropped the
  symlinked-`.flow/` and Windows-Ctrl-C probes** (flow-next's real sore spots: symlinked `.flow/` is a
  common repo convention; Windows signal handling is live post-fn-77). E4's coarse "majority-of-gaps"
  binary still scored PASS, hiding it — but it is a genuine coverage loss. The prune cue meant for
  *well-specified* specs bled into thin ones.
- **E1–E3 accuracy held 12/12** (no eval-registered regression), BUT there IS a qualitative regression
  (the I1 probe drop above). Tokens +144. Lever's failing quality cell = **I3-E5** (run1 FAIL, run2
  PASS → tie; a tied N=2 cell scores FAIL, conservative).

**Why REVERT (grounds, in order):**
1. **The I1 thin-spec coverage regression** — the strongest ground. A prune cue that strips genuine NFR
   probes (symlink/Windows) on under-specified specs is a real quality loss on the class interview most
   exists to serve. This alone justifies revert regardless of the aggregate.
2. **The aggregate can't demonstrate a clean win** — quality 7/8(lever, N=2) vs 7/8(baseline, N=1-lucky)
   is NOT like-for-like (asymmetric N; baseline I3 flipped 5/5→3/5 on re-run). A symmetric re-measure
   would be needed to claim `quality↑`; recording a keep on the flat number would launder the ratchet.
3. **Conservative default** — don't mutate a core skill on ambiguous/asymmetric data; +144 tok.

**Honest status:** the diagnosed blind spot is real (interview over-asks on thorough specs — corroborated
by SKILL.md L36's *unqualified* "40+ questions typical"), and the lever fixes it on the target (I4) — but
it is NOT a clean, no-regression win, and the E5 eval is too noisy (N≤2) to ratchet on. NOT "would confirm
as a keep at higher N" — a proper re-attempt must FIRST (a) re-scope the cue to well-specified specs only
so it can't strip thin-spec NFR probes, and (b) add a per-fixture must-ask NFR answer-key + majority-vote
E5 (N≥5) so both the gain AND the I1-style regression are detectable. Only then is keep-vs-revert decidable.

## Experiment 2 — prompt trim — DISCARD-HOLD (considered, not run)
The required 2nd (trim) experiment. interview's trimmable bulk is the question-bank surface
(`questions-technical.md` categories) + SKILL.md verbose sections. **Skipped as unsafe-to-verify:**
reducing question breadth is **coverage-load-bearing** — exp-1's own I1 regression (probes dropped when
interview was nudged to ask less) is direct proof that trimming the question surface drops NFR coverage;
and any trim to prose the emission run-trick doesn't exercise "holds trivially" = weak-ratchet (per
plan/capture). No safe verifiable trim. Follow-up: a coverage answer-key eval (must-ask NFR list per
fixture) is a prerequisite before a question-surface trim could ratchet safely.

## Net
Baseline confirms interview's questions are strong (fable-judged) EXCEPT over-asking on well-specified
specs (a real, corroborated blind spot). Lever reverted — PRIMARY ground: it strips genuine NFR probes
(symlink/Windows) on thin specs (the I1 regression); the noisy-aggregate is a secondary factor. No prose
change. Durable deliverables: a **fable-judged question-quality eval suite** for a core skill, a diagnosed
blind spot, and two concrete follow-ups (re-scope the prune cue to well-specified specs only; add a
per-fixture must-ask-NFR answer-key + majority-vote E5 at N≥5 before re-attempting).

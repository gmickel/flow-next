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

## Experiment 3 - frontier rounds (fn-100) - SHIPPED - accuracy 12/12, quality 7/8, 13,242 -> 13,754 tok
2026-07-18, fn-84.3 protocol (sonnet emission runs, blind fable E4/E5 judges, host-scored E1-E3) plus a
rounds-specific host check: frontier partition - no question grouped in a round with its own open
prerequisite. Note: tokens measured as bytes/4 of the technical-scope loaded set immediately before/after
the fn-100 edits (52,970 -> 55,014 B); the 12,314 figure in rows 0-2 is the historical fn-84 file state.

**Mutation (SKILL.md Question Order rewrite):** the depth-first one-call-per-turn walk becomes frontier
rounds - model the interview as a design tree; each round asks the entire frontier (every question whose
prerequisites are settled), split across calls of up to 4 grouped by topic and announced as one round;
recompute the frontier once per round, announce pruned branches at the next round's opener; branch depth
caps at 4 rounds. Dependency discipline explicit: a question never rides in the same round as its own
prerequisite.

**First pass (v1, N=2 per arm per fixture):** accuracy E1-E3 12/12 on every rep of BOTH arms; partition
correct on all rounds runs; I4 restraint sharpened (1 Q vs baseline 2, explicit already-settled ledger);
I2 rounds beat baseline on E4 (PASS,PASS vs FAIL,PASS); I3 near-parity (E4 PASS,FAIL / E5 PASS,PASS).
But **I1 thin lost E5 both reps** (rounds-v1 E4 FAIL,FAIL / E5 FAIL,FAIL vs baseline E4 FAIL,FAIL /
E5 PASS,PASS): the draft rule "never hold a frontier question back" licensed queued cosmetic follow-ups
that judges scored as padding.

**Fix (v2, the shipped wording) - "a frontier slot is earned":** every genuinely open decision joins the
round and NFR probes ALWAYS qualify however thin the spec (guarding the exp-1 trap where an unscoped
prune cue dropped thin-spec NFR probes), but pure-cosmetic polish folds into a related question's options
or a stated write-back default. I1 re-run at N=3 under v2: **E4 3/3 PASS (baseline was 0/2), E5 3/3
PASS**, partition correct - the freed slots went to substantive probes (change-detection mechanism with
scale rationale, repo-size, Windows/SIGTERM nuance, retry-exhaustion chain). Guard reps I3/I4 under v2
(bleed check, N=1 each): I4 PASS/PASS with a single question that surfaced a genuine R1-vs-R4 contract
gap no other run in the eval found, and fold-as-stated-default fired exactly as written; I3 E5 PASS with
both DECIDED boundaries intact and content near item-for-item with the passing baseline reps (plus a
security probe baseline lacked) - its E4 FAIL is documented judge-counting noise on that fixture (judges
split all session on crediting append-perf from the append-mode rationale, and on an R-ID-gap probe no
run in any arm ever asked). No bleed detected.

**Partition: 11/11 partition-scored rounds runs, zero intra-round dependency violations** - every
dependent question deferred with an explicit unblocked-by annotation; conditional prunes announced.
Scored population: the 8 v1 runs + the 3 v2 I1 re-runs. The 3 v2 guard reps (I2/I3/I4) were not
separately partition-scored (14 rounds emissions total; 11 in the partition denominator).

**Row mapping (v2-only observations):** quality 7/8 = I1 2/2 (N=3) + I2 2/2 + I3 1/2 (E4 tie-broken FAIL
per the conservative rule - the documented noise above) + I4 2/2; runs=6 (3+1+1+1 v2 emissions; the 8 v1
rounds runs and baseline comparison reps stay in this prose, never in the row).

**Verdict - SHIPPED:** accuracy floor holds, quality >= baseline under v2, and adaptation checkpoints
collapse from one per call to one per round (emission: 1-3 rounds vs 2-4 sequential baseline calls;
live-host turn/latency effects are platform-dependent and get validated in dogfood, not claimed from the
eval). E5 remains an advisory-noise eval at low N per the fn-84 ledger; the hard guards are the accuracy
floor + E4 + the partition check.

**Ledger-contract note (feature validation, not an optimization ratchet):** the header's keep rule
(accuracy >= baseline AND (accuracy-up OR tokens-down OR quality-up)) governs prompt-OPTIMIZATION
experiments; this entry does not claim it. Experiment 3 records a protocol FEATURE change (spec fn-100)
validated on this harness as a regression gate: ship criteria were accuracy floor held (12/12), quality
>= baseline under the shipped v2 wording, and a clean frontier partition - with the +512 B (+128
tok-equiv) accepted as feature cost, and the structural win (adaptation checkpoints one-per-round
instead of one-per-call) living outside the TSV's scored columns. `status=shipped` marks the fn-100
ship decision, not a ratchet keep; the ratchet audit rule continues to apply, unmodified, to future
optimization rows.

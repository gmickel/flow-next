# Binary evals (4) — max_score = 4

**Extended-schema split (fn-84):** E1–E3 are ACCURACY (accuracy_max = **3**, the floor — audit is
FINDER-SHAPED, so the over-flag guard E2 is load-bearing). **E4 is the QUALITY-lever scoring eval**
(Consolidate discrimination; quality_max = **1**), authored BEFORE baseline (Major-B). Scored on the run's
emitted per-entry verdicts vs the frozen answer keys in `test-inputs.md`. Model held constant: **sonnet**;
`mode:autofix`. **Frozen contexts are RAW FACTS (no verdict adjectives) — the run must DERIVE each verdict**
(fn-84.5 fable-review fix; the earlier conclusion-stating contexts spoon-fed the answers).

Ratchet: accuracy never drops; keep iff accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑).

---

EVAL 1: Classification correctness  [ACCURACY] — M1 (a,b,c,f,g) + M3-b, 6 scored entries
Question: Do all 6 get an answer-key-accepted verdict — M1-a Keep, M1-b Update (rename → fix reference,
not Replace), **M1-c mark-stale** (facts show code gone BUT 'superseded by flow-next-tui' → problem may persist in the successor + no evidence to Replace → ambiguity), M1-f Replace/supersede, M1-g mark-stale, **M3-b ∈ {Update, mark-stale}** — with
ALL 6 correct?
Pass: 6/6 accepted; the Delete-vs-mark-stale AND Update/Replace boundaries respected (M1-b is a reference-drift Update NOT a Replace;
M1-f is an anti-pattern Replace NOT an Update; M3-b is Update or mark-stale, NOT Replace/Delete/Keep).
Fail: ≤5/6 — ANY miss registers (e.g. the Update↔Replace boundary inverted, M1-c guessed Delete/Replace instead of mark-stale on genuine successor-ambiguity, or M3-b Kept (a now-wrong value left in place) / Replaced / Deleted.

EVAL 2: Over-flag guard on the CLEAN + LOOKS-STALE corpus  [ACCURACY] — M2 (4) + M3-a (finder-shape, load-bearing)
Question: For M2's 4 entries AND M3-a (whose raw facts show the N+1 code present+unfixed despite the entry's
8mo age / 'old ORM' aside), does audit classify ALL 5 **Keep** — deriving "still accurate" from the code
facts and inventing zero Delete/Replace/Consolidate/mark-stale findings?
Pass: all 4 M2 + M3-a → Keep; zero false positives (surface age / prose color does NOT trigger a Delete/stale).
Fail: ANY of the 4 M2 entries **OR M3-a** marked Delete / Replace / Consolidate / mark-stale (a fabricated
problem on healthy memory, or over-flagging a still-valid entry as stale on surface signals).

EVAL 3: Delete-discipline + ambiguity → mark-stale  [ACCURACY] — M1
Question: Does audit AVOID over-deletion — no accurate entry deleted/replaced — AND route BOTH genuinely-ambiguous
entries to **mark-stale** (M1-g: un-round-trippable YAML + unresolved module; M1-c: code gone but a 'superseded by' successor leaves the problem domain unresolved) rather than guessing Delete? (The corrected suite has NO clean-Delete case — a fixture gap noted in test-inputs.md; delete-discipline here is tested as restraint + correct mark-stale routing.)
Pass: zero accurate entries deleted; M1-c AND M1-g → mark-stale on their genuine ambiguity; no Replace shipped without a trustworthy successor.
Fail: an accurate entry deleted, M1-c/M1-g guessed (Delete/Update/Replace) instead of mark-staled, or a Replace on insufficient evidence.

EVAL 4: Consolidate discrimination — both directions  [QUALITY-LEVER SCORING EVAL] — M1-d/e + M3-c1/c2
Question: (i) The M1-d/e pair (same bug, but EACH carries unique content — d's `$LEAF` example + principle,
e's `.flow/tmp` fix pattern) → **content-preserving Consolidate** (merge both uniques into one canonical;
Delete-one is content-lossy here, Keep-both leaves duplication). (ii) The M3-c1/c2 pair (standing invariant vs
dated incident + root-cause/prevention) → **{Keep-both OR a Consolidate that RETAINS c2's root-cause+prevention}**.
Pass: M1-d/e Consolidated preserving both uniques (not Delete-one, not Keep-both) AND M3-c handled per its
accept-set (Keep-both, or a content-preserving merge).
Fail: M1-d/e Delete-one (loses e's fix pattern) or Keep-both (duplication); OR M3-c over-Consolidated in a way
that DROPS c2's root-cause/prevention (content-lossy), Delete-one'd, or mark-staled.

# Binary evals (4) — max_score = 4

**Extended-schema split (fn-84):** E1–E3 = ACCURACY (accuracy_max = **3**, the floor — prospect's critique is
a REJECTER, so the over-reject guard E2 is load-bearing). **E4 = the QUALITY-lever scoring eval** (taxonomy
precision; quality_max = **1**), authored BEFORE baseline (Major-B). Scored on the run's emitted per-candidate
`{verdict, taxonomy, reason}` vs the frozen answer keys in `test-inputs.md`. Model held constant: **sonnet**.
The **rejection-floor check is HARNESS-COMPUTED** from the emitted verdicts (the critique emits YAML only; it
never self-reports the floor). Ratchet: accuracy never drops; keep iff accuracy ≥ baseline AND (accuracy↑ OR
tokens↓ OR quality↑).

---

EVAL 1: Classification + taxonomy correctness  [ACCURACY] — C1 (9 candidates)
Question: Does each C1 candidate get its answer-key verdict AND (for drops) an accept-set taxonomy slug —
C1-1 keep, C1-2 duplicates-open-epic, C1-3 too-large, C1-4 insufficient-signal, C1-5 out-of-scope,
C1-6 out-of-scope-vs-strategy, C1-7 backward-incompat, C1-8 keep, C1-9 keep — with ≥8 of 9 correct (verdict
AND slug both right)?
Pass: ≥8/9 correct. Fail: ≤7/9, OR a verdict inverted on ANY of these hard cases — a good grounded candidate
dropped (C1-1 / C1-8 / C1-9) OR a clear reject kept (**C1-2, C1-3, C1-4, C1-5, C1-6, C1-7** — all six obvious
rejects are protected; keeping the on-mission-XL drift-detection candidate or the telepathic-spec candidate is an automatic fail).

EVAL 2: Over-reject guard on the mostly-good batch  [ACCURACY] — C2 (finder-shape guard, load-bearing)
Question: On C2 (5 grounded good candidates + 1 genuine duplicate), does the critique keep ALL 5 good
candidates and drop ONLY C2-5 — rather than FABRICATE weak rejections of good candidates to reach the 40%
floor? (The critique emits YAML verdicts only; the harness then computes `rejection_rate = drops/total` and
confirms it is < 0.40, proving the critique did NOT pad rejections to satisfy the floor.)
Pass: C2-1/2/3/4/6 all keep; C2-5 drop/duplicates-open-epic; harness-computed rejection_rate ≈ 0.17 (< floor).
Fail: ANY of C2-1/2/3/4/6 dropped (over-rejection to hit the floor — the finder-shape failure) OR C2-5 kept.

EVAL 3: Taxonomy discipline  [ACCURACY] — C1 + C2
Question: Does every `drop` use ONLY a frozen 7-slug value (no invented reason strings); does EVERY
`out-of-scope-vs-strategy` emission (C1-6, and any other candidate the critique routes there) cite the
violated track **"Zero-dependency core"** verbatim in `reason`; is every `duplicates-open-epic` (C1-2,
C2-5) anchored to the actual open spec `fn-70` in the snapshot (not a hallucinated duplicate); and is `other`
used zero times?
Pass: all slugs ∈ the frozen set; every o-o-s-v-s cites the track verbatim; every dup anchored to fn-70;
`other` count = 0. Fail: an invented slug, a `duplicates-open-epic` with no real snapshot anchor (hallucinated
dup), a missing strategy-track citation on an o-o-s-v-s drop, or `other` used where a specific slug fits.

EVAL 4: Taxonomy precision  [QUALITY-LEVER SCORING EVAL] — C1
Question: Does the critique pick the MOST-specific correct slug rather than a generic fallback — C1-2
duplicates-open-epic (NOT out-of-scope), C1-3 too-large (NOT keep and NOT insufficient-signal — the idea is
on-mission + grounded, so `size: XL` is the sole defect; the critique must reject on size, not keep it because
it's aligned), C1-5 out-of-scope (NOT too-large — `size: S`, and NOT insufficient-signal), C1-7
backward-incompat (NOT too-large or out-of-scope)?
Pass: all four specific-vs-generic boundaries resolved to the specific slug. Fail: any of the four collapsed to
a vaguer slug (e.g. C1-2 as out-of-scope, C1-7 as too-large) — a precision loss even when the drop verdict is right.

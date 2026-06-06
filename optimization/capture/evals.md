# Binary evals (5) — max per run = 5; max_score = 5 × 3 inputs = 15

All five are ACCURACY evals (R3 ≥2–3 satisfied strongly — this is an accuracy-critical skill;
`spec.md` is USER-AUTHORITATIVE). A token-trim mutation is kept ONLY if it holds all of these.

Scoring scope per input:
- C1, C2 produce a printed read-back payload (Phase 4.4 autofix print). Score E1–E5 on that payload.
- C3 produces a REFUSAL (no draft). For C3, E4 is the load-bearing eval; E1/E2/E3/E5 are scored
  N/A→pass only if the refusal is correct (a correct refusal trivially can't fabricate/mistag/leak).
  If C3 wrongly emits a draft, E4 FAILS and E1/E2/E3/E5 are scored on that (wrong) draft.

EVAL 1: Fidelity / grounded  [ACCURACY]
Question: Does every acceptance criterion + every Goal/Boundary line trace to the conversation
evidence, with NO fabricated requirement and NO tech-stack the user never stated?
Pass: every `[user]`/`[paraphrase]` line maps to a real conversation turn; every non-conversation
line is honestly tagged `[inferred]`; zero invented tech-stack (R10).
Fail: any requirement with no conversational basis presented as `[user]`/`[paraphrase]`, or any
unstated technology named in the spec body.

EVAL 2: Source-tagged correctly  [ACCURACY]
Question: Does every acceptance criterion carry exactly one of `[user]`/`[paraphrase]`/`[inferred]`,
AND do business-routed lines (Goal/Boundaries/Motivation) carry ONLY `[user]`/`[paraphrase]` (never
`[inferred]` in a biz destination, per R24)?
Pass: every AC tagged with exactly one tag; no `[inferred]` in a biz-routed line.
Fail: any untagged/double-tagged AC, or an `[inferred]` line routed into a business section.

EVAL 3: Read-back surfaced  [ACCURACY]
Question: Does the output include (a) the `## Conversation Evidence` verbatim block, AND (b) the
source-tag tally line `Source: [user] N · [paraphrase] M · [inferred] L` with a per-section
`[inferred]` breakdown?
Pass: both the evidence block and the tally (with [inferred] breakdown) are present.
Fail: missing evidence block, or missing/!malformed tally, or no [inferred] surfacing.

EVAL 4: Respects user override / no silent overwrite  [ACCURACY] — the R5 guard
Question: On C3 (existing user-edited spec, no --rewrite), does capture REFUSE (surface the conflict
/ exit 2) rather than emit a fresh draft that would create a competing or overwriting spec?
Pass (C3): refuses — names the overlapping spec id and the autofix "cannot resolve duplicates / re-run
with --rewrite" path; emits NO full spec draft.
Pass (C1, C2): no existing-spec collision in the input → trivially satisfied (capture proceeds
correctly; it did not silently clobber anything).
Fail: C3 emits a full draft / proceeds as if creating a fresh spec, ignoring the existing fn-91 and
its hand-edited boundary.

EVAL 5: Core sections present + no forbidden content  [ACCURACY / FORMAT]
Question: Does the draft carry the core sections (`Conversation Evidence`, `Goal & Context`,
`Acceptance Criteria`, `Boundaries`) AND obey forbidden-behaviors (no code snippets, no specific
file paths in the spec body, Decision Context FLAT vs SUBSTRUCTURED chosen correctly for the input)?
Pass: core sections present; no code blocks / file paths in the body; Decision Context shape correct
(C1 FLAT; C2 SUBSTRUCTURED with ### Motivation). (C3: N/A→pass when E4 refusal is correct.)
Fail: a core section missing, a code snippet/file path leaked into the body, or wrong Decision
Context shape.

# Binary evals (6) — max per run = 6; max_score = 6 × 3 inputs = 18

**fn-84.2 extended-schema split:** E1–E5 are ACCURACY (accuracy_max = 5 × 3 = **15**, the
zero-quality-loss floor); **E6 is the QUALITY-lever scoring eval** (`[inferred]`-tagging discipline;
quality_max = 1 × 3 = **3**), added here BEFORE the fresh baseline (Major-B). This is an
accuracy-critical skill (`spec.md` is USER-AUTHORITATIVE); a mutation is kept only if accuracy holds
AND (tokens↓ OR quality↑). Model held constant: **opus** (matches this suite's prior rows).

Scoring scope per input:
- C1, C2 produce a printed read-back payload (Phase 4.4 autofix print). Score E1–E6 on that payload.
- C3 produces a REFUSAL (no draft). For C3, E4 is the load-bearing eval; E1/E2/E3/E5/E6 are scored
  N/A→pass only if the refusal is correct (a correct refusal trivially can't fabricate/mistag/leak).
  If C3 wrongly emits a draft, E4 FAILS and E1/E2/E3/E5/E6 are scored on that (wrong) draft.

EVAL 1: Fidelity / grounded  [ACCURACY]
Question: Is the spec CONTENT grounded — no fabricated requirement invented out of nothing, and no
tech-stack the user never stated? (This is a CONTENT-fidelity check; tag DIRECTION is E6's job.)
Pass: every requirement in the body traces to a real conversation turn or is an honest agent
elaboration surfaced as such; zero invented tech-stack (R10).
Fail: a requirement with NO conversational basis appears at all (fabrication), or any unstated
technology is named in the spec body.

EVAL 2: Source-tagged correctly  [ACCURACY]
Question: Does every acceptance criterion carry exactly one of `[user]`/`[paraphrase]`/`[inferred]`,
AND does every line that carries a §2.6-routed BUSINESS SIGNAL the user stated (a target-user /
success-metric / motivation) carry ONLY `[user]`/`[paraphrase]` (never `[inferred]`, per R24)?
NOTE: the prohibition is on mis-tagging a real USER biz-signal — an agent-inferred scoping non-goal
in Boundaries is legal `[inferred]` (workflow.md L298/L325 expect `[inferred]` in Boundaries); a
biz-labeled *section* is not itself off-limits to `[inferred]`.
Pass: every AC tagged with exactly one tag; no user-stated biz signal (metric/target-user/motivation)
mis-tagged `[inferred]`.
Fail: any untagged/double-tagged AC, or a user-stated business signal tagged `[inferred]`.

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

EVAL 6: `[inferred]`-tagging accuracy  [QUALITY-LEVER SCORING EVAL — the [inferred]-discipline lever targets this]
Question: Is every `[inferred]`-tagged line genuinely NOT traceable to a user turn (no user-STATED
requirement mislabeled `[inferred]` — over-tagging), AND is every user-stated requirement tagged
`[user]`/`[paraphrase]` rather than `[inferred]` (no false agent-attribution — under-crediting)?
Pass: `[inferred]` appears ONLY on lines with no conversational basis (a genuinely agent-supplied
detail the user never stated); every requirement the user did state is `[user]`/`[paraphrase]`.
(C3: N/A→pass on a correct refusal.)
Fail: a user-stated line is tagged `[inferred]` (over-tag), OR an agent-invented line is presented as
`[user]`/`[paraphrase]` (under-tag / false attribution). Distinct from E1 (CONTENT fidelity — no
fabricated requirement / invented tech, tag-agnostic) and E2 (exactly one tag + no user biz-signal
mis-tagged); E6 owns TAG DIRECTION — no user-stated line → `[inferred]`, no agent line → `[user]`/`[paraphrase]`.

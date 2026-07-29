## Goal & Context
<!-- scope: business -->

A benchmark of our spec template against an alternative section list concluded **change
nothing** - the wider template's quality gain did not survive a pre-registered replication
and it cost ~34% more length. Full record: `~/work/agent-evals`,
`studies/spec-format-2026-07`.

But the comparison surfaced two things that were genuinely better in the reference spec and
are **not sections at all** - they are demands on the *prose* a spec contains. Both are
cheap to express as template guidance and neither adds machinery:

1. **Measured, not asserted.** Where our specs would write "this dependency is unstable",
   the reference spec wrote the measurement: a release workflow hard-coding `semver -i
   minor`, 76 versions in 12 months, 41 icons changing geometry under an unchanged name at
   a median displacement of 1.02 units on a 24-unit grid. The decision became unarguable
   instead of asserted. Our messaging discipline already says proof-backed never
   adjective-backed; we do not apply it to specs.

2. **Verified facts separated from inferred ones.** A block of environment facts marked
   "verified in `node_modules` rather than inferred" (a pinned exact version, an unbound
   keybinding, an API that does not exist, a failure mode that kills document load), plus
   decisions the spec flagged as its own inference and asked to have confirmed before the
   build session committed to them.

Note what (2) actually is: the provenance *idea* behind our `[inferred]` tag, applied to
**technical facts and decisions** rather than to acceptance criteria. The affordance already
exists in one place and is demonstrably useful there.

**What this spec is NOT.** It is not "add more tags." Depends on
[fn-147](fn-147-source-tags-in-interview-provenance-for.md), which is the tag work:
extending the existing four-tag vocabulary to the acceptance criteria that
`/flow-next:interview` writes. fn-147 needs no eval - the tags are proven in capture and
the parser already reads them from any writer - so it is a feature, not research.

This spec tests something different: whether two **demands on the prose** improve a spec.
Only one of the two is provenance-flavoured at all:

- Arm M (measured claims) has nothing to do with tags or provenance.
- Arm V targets a **different surface** - environment/codebase facts in the technical
  sections, and decisions resting on an inference - and plausibly a different mechanism
  (the reference spec used a prose block, "verified in `node_modules` rather than
  inferred", not a per-bullet suffix). Whether it should reuse fn-147's `[...]` grammar or
  stay prose is itself an open question this eval should answer.

**Sequencing is a design constraint, not scheduling preference.** fn-147 ships first so
that (a) the vocabulary and the reader habit already exist, making arm V cheaper to express
and able to reuse one single-sourced definition instead of forking a parallel one, and
(b) arm V cannot be credited with an effect that fn-147 actually produced.

The question this spec answers is whether adding either demand to the template's guidance
prose measurably improves downstream outcomes, or whether it is another intuition that
evaporates under replication. **A null result is a valid and expected outcome** and ships
nothing.

## Architecture & Data Models
<!-- scope: technical -->

Research, executed in `~/work/agent-evals` (private), not in this repo. Nothing lands in
flow-next unless the eval clears its pre-registered bar.

Reuse of existing harness (do not rebuild):

- `lib/evalkit.py` - anchored answer parsing, blind labelling, the paired decision rule
  with its `INCONCLUSIVE` branch.
- `METHODOLOGY.md` - the five rules. All five bind here, in particular rule 4 (a key mined
  from a shipped diff mixes requirements with the author's incidental choices) and rule 5
  (a guard eval must not reward the degenerate answer).
- `docs/fixtures.md` - fixtures referenced by commit SHA, recreated as worktrees, `.flow/`
  parked out, leak-checked by grep before use.

**Intervention under test** is guidance prose added to the *bundled* template's section
bodies - not new sections:

- Arm M ("measured"): a rule that a risk, constraint or dependency claim carries its
  measurement or names it unmeasured.
- Arm V ("verified"): a rule that environment/codebase facts are marked verified or
  inferred, and that decisions resting on an inference say so.
- Arm MV: both.
- Arm A0: current template, unchanged.

**Fixture requirement that differs from the last study.** The one clean signal last time
landed on the only bug/root-cause fixture, generating the pre-registered hypothesis that
these interventions pay on debugging-shaped work and not greenfield. This eval must
therefore stratify by work shape - at least 2 bug/root-cause and 2 greenfield/feature
fixtures - so shape is a reportable dimension rather than a confound. Reuse F1/F2/F3 where
they fit and mine new ones for the gap.

## API Contracts
<!-- scope: technical -->

No product API. Study contract:

- `studies/spec-prose-<YYYY-MM>/PREREGISTER.md` written and committed **before any draw**,
  declaring: the single primary endpoint, the decision thresholds, which cuts will not be
  reported, and what a positive result licenses.
- Arm instruction files generated from ONE shared preamble string with byte-identity of the
  shared part verified, so arms differ only in the guidance under test.
- Blind labels; the arm map lives outside the blind directory and is never given to a
  scorer or subject.
- Every draw published, including ones that go the wrong way, plus every discard, in
  `changelog.md`.

## Edge Cases & Constraints
<!-- scope: technical -->

- **These two candidates can silently inflate length.** "Carry the measurement" invites
  paragraphs. Spec size is a first-class cost measured on both axes, because +34% is what
  sank the last candidate.
- **Rule 5 applies sharply here.** An eval that rewards "mentions a number" will be gamed
  by a spec inventing precision. The measured-claims eval must check the number is
  *traceable to something a reader can check*, not merely present.
- **Arm V risks the uniform-tagging failure** already flagged in the companion spec
  (fn-147): if every fact gets marked inferred, the distinction carries no signal. A
  discrimination check is mandatory, not optional.
- **Single-repo overfit persists** unless a second sandbox is added. Declare it either way;
  prefer adding a contrasting repo since the last study could not.
- **Do not reuse the last study's invalidated key items.** F1 L9, F3 M4 and F3 M9 were
  judged design-preference rather than requirement. They stay dropped.
- **fn-147 is a hard prerequisite, and the reason is measurement integrity.** Arm V and
  fn-147 both touch provenance. If they land in the same window, an arm-V gain could
  actually be fn-147's effect. fn-147 first, its behaviour settled, then arm V measured on
  top of it as the baseline - and the fixtures used for this eval must be authored under
  post-fn-147 behaviour so the baseline arm already carries criteria tags. A baseline that
  predates fn-147 would make arm V look better than it is.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A pre-registered study exists under `~/work/agent-evals/studies/` with its
  endpoint, thresholds and decision rule committed **before** the first draw, following
  `METHODOLOGY.md`.
- **R2:** Fixtures are stratified by work shape (>= 2 bug/root-cause, >= 2
  greenfield/feature) and referenced by commit SHA with a passing leak check.
- **R3:** Arms are A0 / M / V / MV, generated from one shared preamble with byte-identity of
  the shared portion verified.
- **R4:** The screen runs one draw per cell to identify a candidate; any candidate then goes
  to a paired replication of >= 3 draws per cell before any keep decision.
- **R5:** Both cost axes are measured and reported per arm: spec characters and the
  downstream consumer's output, not quality alone.
- **R6:** The measured-claims eval verifies a cited number is traceable to a checkable
  source, and does not credit unsupported precision.
- **R7:** The verified-vs-inferred eval includes a discrimination check that fails a spec
  which marks facts uniformly.
- **R8:** The verdict is reported through the pre-registered rule with no post-hoc
  substitution, and `INCONCLUSIVE` is reported as such when draw noise matches the effect.
- **R9:** Every draw and every discard is published, including those contradicting the
  hypothesis.
- **R10:** A null or inconclusive result closes this spec with no flow-next change, and that
  is recorded as the outcome rather than treated as failure.
- **R11:** The study ends in a report + human handover, never an autonomous template edit.
  On CONFIRMED, the report carries the exact winning guidance prose as a ready-to-apply diff
  against `plugins/flow-next/templates/spec.md`, with its measured cost - so the human
  go/no-go is the only remaining step, and on "go" the change is implemented directly (it is
  a small prose diff backed by the eval evidence; no further spec required). On NOT
  CONFIRMED / INCONCLUSIVE the handover recommends closing with no change.
- **R12:** The report states whether the effect varies by work shape, addressing the
  standing bug-shape hypothesis from `studies/NEXT.md`.

## Boundaries
<!-- scope: business -->

- **No autonomous template edit.** The study's terminal artifact is a report + human
  handover carrying the ready-to-apply diff (R11); the template changes only after the
  human says go, and then directly - no intermediate spec.
- **No new sections.** That question is settled - the answer was no. This tests prose
  demands inside existing sections.
- **Not the F2 implementation study.** The approved-not-started code-quality study in
  `studies/NEXT.md` stays separate; do not fold it in.
- **No public comparison claims.** Nothing here licenses ranking copy on flow-next.dev, and
  no shipped artifact names any upstream project. Defending our own decisions is the only
  sanctioned public register.
- **Not a rebuild of the harness.** Reuse `lib/evalkit.py` and the methodology; extend only
  where a genuinely new eval shape is needed.

## Decision Context
<!-- scope: both -->

### Motivation

Two concrete, cheap candidates surfaced from a study that otherwise said "change nothing" -
and both are prose demands rather than structure, which is the class of change with the best
cost profile we have (no machinery, no new sections, no per-section length tax by
construction). They are worth measuring precisely because the last intuition of this kind
looked good and did not replicate; the discipline that caught that is now cheap to re-run.

The second candidate is also strategically interesting: it generalises the source-tag idea
from acceptance criteria to facts and decisions, and the tags are already field-proven as
the one place a reviewer can skip model judgement entirely.

### Implementation Tradeoffs

**Prose demands over sections, deliberately.** A section is a fixed cost paid on every spec
whether it earns it or not; a demand inside an existing section only costs where it applies.
That is the main reason these two are worth testing when the section experiment failed.

**Stratifying by shape is the design change from last time.** The previous study's single
clean cell was its only bug-shaped fixture, and noticing that after the fact is exactly the
move pre-registration exists to prevent. Building shape in as a declared dimension converts
last study's accident into this study's hypothesis.

**Expect a null and budget for it.** Two rounds have already landed there. The value bought
is a defensible answer on a cheap intervention, not a win.

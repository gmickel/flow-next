## Goal & Context
<!-- scope: business -->

`/flow-next:capture` tags every acceptance criterion it writes with its provenance -
`[user]` (the user's words), `[paraphrase]` (their meaning tightened), `[inferred]` (the
agent's own inference), `[strategy:<track>]` (traced to a STRATEGY.md track). Those tags
are load-bearing: capture's read-back refuses to recommend `approve` while unverified
`[inferred]` items remain, and 3.7.0 documented how to use them afterwards - tally
grounded-vs-guessed criteria with a grep, then re-interview only the inferred ones.

`/flow-next:interview` emits **no tags at all.** Verified: zero occurrences of any source
tag across the interview skill tree. So every one of those affordances is unavailable to
anyone whose specs come from interview rather than capture - which is a large share of
users, because interview is the entry point for the symmetric PO -> tech-lead flow and for
refining an existing spec. The 3.7.0 recipes silently return an empty tally on an
interview-authored spec.

Tags matter *more* in interview than in capture, not less. Capture synthesizes one
conversation; interview runs a business pass and a technical pass that each append
criteria under append-only numbering. "Did the PO state R7, or did the technical pass
infer it while filling gaps?" is exactly the question a later reviewer needs answered, and
today the spec cannot answer it.

The flowctl parser is already source-agnostic - it extracts the last `[...]` token from any
`- **R<N>:**` bullet regardless of which skill wrote it. So this is a prompt-side change to
what interview emits, not a parser change.

## Architecture & Data Models
<!-- scope: technical -->

No new machinery. The tag vocabulary, the parse, and the consumers already exist:

- **Vocabulary + semantics:** owned by capture today, and deliberately **repeated** across
  `skills/flow-next-capture/{SKILL,phases,workflow}.md` rather than centralised (fn-84.2
  proved relocating it regresses accuracy). Interview gets the same short guidance at its
  own emission sites; drift is prevented by a test, not by DRYing the prose.
- **Parser:** `_export_parse_acceptance_criteria` in `flowctl.py` extracts the trailing
  `[...]` token into a `tag` field. Source-agnostic, unchanged by this spec.
- **Writers to change:** `skills/flow-next-interview/` - the R-ID emission sites in
  `references/write-back.md` (NEW IDEA branch, EXISTING SPEC branch, and the merged-body
  contract) plus whatever `SKILL.md` says about acceptance-criteria authoring.
- **Codex mirror:** skills/references are mirrored; `sync-codex.sh` twice.

Design questions this spec must settle, not assume:

1. **Per-pass semantics.** Under `--scope=business` the actors are the PO and the agent;
   under `--scope=technical` they are the tech lead and the agent. Does `[user]` mean "the
   human in *this* pass", with the pass identity recoverable some other way, or does the
   vocabulary need a pass dimension? Prefer the former (fewer tags, no new grammar) unless
   the eval shows reviewers cannot tell business-stated from technical-stated criteria
   apart when they need to.
2. **Append-only interaction.** A later pass appends criteria with the next unused number
   and must not rewrite earlier ones. So a pass tags only the criteria it adds, and never
   retags an existing bullet - retagging would silently rewrite provenance the earlier pass
   asserted. This is a hard invariant, not a preference.
3. **Untagged legacy criteria.** Existing specs have untagged R-IDs. A pass encountering
   one leaves it untagged (see invariant above). Consumers must treat "no tag" as unknown
   provenance, never as `[user]`.
4. **Does interview inherit the no-self-blessing rule?** Capture will not recommend
   `approve` while unverified `[inferred]` items remain. Interview is an interactive Q&A
   whose whole purpose is resolving uncertainty, so the same rule may be either redundant
   (the questions already did the verifying) or valuable (it catches criteria the agent
   invented while drafting rather than asked about). Decide with evidence, and record the
   decision either way.

## API Contracts
<!-- scope: technical -->

No CLI surface changes required. Tag format is fixed by the existing parser:

```
- **R<n>:** <criterion text> [user]
- **R<n+1>:** <criterion text> [inferred]
```

Trailing token, last `[...]` on the bullet, lowercase, no spaces inside. `[strategy:<track>]`
carries a colon and a track slug.

Deliberately **out of scope as an API change, but recorded as a known gap:** `flowctl spec
export-cognitive-aid --json` does not expose parsed criteria with their tags as a top-level
array - the parse feeds the PR-body coverage table internally. The documented consumer route
is therefore a grep over `flowctl cat`. If the eval shows tags are being used
programmatically enough to justify it, a `flowctl spec criteria --json` surface is a
follow-up spec, not this one.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Never retag an existing criterion.** Provenance asserted by an earlier pass is
  frozen exactly like the R-ID number itself.
- **Untagged is not `[user]`.** Absence means unknown, and any consumer that defaults it to
  "stated by a human" is wrong in the dangerous direction.
- **A tag must not be guessable from position.** If a pass tags everything it writes
  `[inferred]` because that is the safe default, the tag carries no information and the
  tally becomes noise. Honest discrimination is the whole value; a uniformly-tagged spec is
  a failure, not a pass.
- **Prompt-weight budget.** Interview is an accuracy-critical skill with a documented
  history of regressing on "obviously safe" prose edits (a prune cue in fn-84.3 fixed one
  fixture and dropped NFR probes on another). The tag guidance must be short and sit at the
  emission site, not as a distant reference - proximity is load-bearing.
- **Do NOT single-source the tag table by relocating it.** This exact experiment already
  failed: fn-84.2 moved capture's duplicated source-tag + biz-routing tables out to a
  cross-linked file as a self-evidently safe DRY trim, regressed a fixture (15 -> 14) and was
  reverted, with the conclusion that the duplication is accuracy-load-bearing proximity.
  Capture currently repeats its tag guidance across SKILL.md, phases.md and workflow.md on
  purpose. So "cannot drift" must be enforced by a **test** asserting the definitions match,
  not by DRYing the prose into one location.
- **No new questions.** This must not lengthen the interview. Tagging is a property of how
  a criterion is *written down*, not an extra thing to ask about.
- **Cross-platform.** Canonical prose, `sync-codex.sh` twice, guards green.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `/flow-next:interview` emits a source tag on every acceptance criterion it
  newly writes, using the existing vocabulary (`[user]` / `[paraphrase]` / `[inferred]` /
  `[strategy:<track>]`), in the trailing-token format the current parser already extracts.
- **R2:** An interview pass never adds, changes, or removes a tag on a criterion it did not
  author in that pass; untagged legacy criteria stay untagged.
- **R3:** Interview's tag definitions match capture's, and a test pins them so the two
  cannot drift. **Achieved without relocating tag guidance away from its emission sites** -
  see the proximity constraint in Edge Cases; a shared cross-linked table is explicitly the
  wrong shape here.
- **R4:** The 3.7.0 tally recipe (grep over `flowctl cat`) returns a non-empty, mixed-tag
  result on a spec authored end-to-end by interview, where today it returns nothing.
- **R5:** Tags discriminate: on a frozen fixture where some criteria are quoted from the
  interviewee's answers and others are agent-drafted gap-fills, the emitted tags separate
  the two rather than collapsing to one value.
- **R6:** The decision on whether interview inherits capture's no-self-blessing rule is
  recorded with its rationale, and implemented or explicitly declined.
- **R7:** Per-pass semantics are settled and documented: a reader can tell what `[user]`
  means under a business pass versus a technical pass.
- **R8:** Interview's measured prompt weight does not grow materially - the guidance is
  short and placed at the emission sites.
- **R9:** Docs updated: `docs/spec-template.md` § source tags stops being capture-only,
  the flow-next.dev cookbook recipes stop implying capture is required, and the
  interview skill page reflects the behaviour.
- **R10:** `./scripts/sync-codex.sh` run twice is idempotent with guards green; full suite
  and `uvx ruff@0.16.0 check .` clean.

## Boundaries
<!-- scope: business -->

- **No new tag vocabulary.** Reuse capture's four. Inventing `[tech-lead]` or similar is a
  separate conversation and would break the existing parser contract's expectations.
- **No parser or CLI change.** `_export_parse_acceptance_criteria` is already
  source-agnostic. A `flowctl spec criteria --json` surface is a follow-up spec.
- **No retroactive tagging of existing specs.** No migration, no backfill pass.
- **Not tagging anything other than acceptance criteria.** Tagging technical facts or
  decisions is the separate research question in the companion eval spec - do not
  pre-empt its outcome here.
- **No change to how many questions interview asks.**

## Decision Context
<!-- scope: both -->

### Motivation

The tags turned out to be one of the highest-leverage things in the spec format precisely
because they let a human skip LLM judgement: reading provenance is a grep, not a review.
That affordance currently exists only for capture users. Since interview is the path most
teams land on - and the only one with the PO/tech-lead split where provenance is genuinely
contested - restricting tags to capture leaves the value mostly unrealised.

### Implementation Tradeoffs

**Prompt-side, not machinery.** The parser already reads tags from any writer, so the
cheapest correct fix is teaching interview to emit them. Adding a flowctl surface first
would be building a query API for data that does not exist yet.

**Why single-sourcing the vocabulary matters more than it looks.** Two skills each
carrying their own prose definition of `[inferred]` will drift, and a drifted tag is worse
than no tag because the tally silently means different things per spec. The proximity rule
(guidance at the action site) pulls the other way - so the resolution is a short imperative
at each emission site plus one shared definition, not a distant reference the pass has to
go fetch.

**The honest risk is uniform tagging.** An agent under uncertainty will reach for
`[inferred]` on everything, which produces a spec that looks rigorously tagged and carries
zero signal. R5 exists to catch exactly that, and it is the criterion most likely to fail
first.

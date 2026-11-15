# capture — from:issue (gated reference)

> Read only when SKILL.md parsed the exact `from:issue` token, which a `flow --auto --from-issue`
> run sends ([issue-start.md](../../flow-next-flow/references/issue-start.md)). The autofix rules
> ([autofix-mode.md](autofix-mode.md)) hold too, with the write authorized; this file says only
> what an issue start changes.

## The issue stands in for the conversation

What follows the token is the issue's identifier. The run hands over the source: the issue body
and its comments, or after an earlier question only the body and the comments since it, plus the
route it chose (feature, defect, refactor, slowness, tiny). Wherever workflow.md reads the user's
turns, read that source. A line is untagged only when it is the issue's own words; the compaction
check (§0.4) does not run.

`## Goal & Context` opens with the issue's own text quoted verbatim (its body, and on re-entry the
answering comments), so the design review that follows compares the spec with the issue itself.

Every acceptance criterion is the issue's words or `[paraphrase]` of them, shaped by the route:
a defect's R-ID is that the reported behaviour stops happening, checked by a failing test; a
refactor's is a pinned characterization of current behaviour; a slowness's is the measured
baseline and its target. A criterion that would need `[inferred]` is a question for the person:
exit 2 with `inferred criterion: <the question>`, writing nothing. Inferred context outside the
criteria stays allowed and tagged.

## Refusals

Exit 2, writing nothing, naming the reason:

- a criterion that would have to be invented (above);
- a duplicate open spec (name it);
- a spec-count proposal of more than one spec (`needs a split`): an issue start never splits.

## Writing

The spec is linked to the issue: §5.2 reads the named issue and mints linked under
`tracker.specIds=tracker`, or links it in flow-id mode ([tracker-integration.md](tracker-integration.md)).
The run passes `--no-plan`, so §5.9b writes the field. Capture never marks the spec ready, never
writes glossary terms and never commits: the run does what is its own. The closing block omits
`Recommended next:`.

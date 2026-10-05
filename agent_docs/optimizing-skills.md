# Optimizing skills and agents

Read this before changing a skill or agent to make it leaner, faster or more accurate, or
before running an evaluation of flow-next behaviour.

## How to study a change

- Follow the maintainer's evaluation methodology (`METHODOLOGY.md` and `lib/evalkit.py` in the
  private agent-evals repository). Contributors without it use an equivalent written protocol:
  pre-register the endpoint and decision rule, hold model, harness and effort constant, change
  one thing, use one scoring standard, screen then replicate, and keep negative and inconclusive
  results.
- Run every draw that can carry a wall-clock verdict sequentially on an otherwise idle machine,
  and record host load per draw. Arms launched together throttle each other unevenly, and naming
  that as a limitation does not remove it from the verdict. A frozen protocol states every
  threshold as a number (no "~3x", "with margin" or "borderline") and bounds every rerun path
  with an attempt count and a terminal outcome such as INCONCLUSIVE.
- A study of how skills behave in Claude Code drives the real terminal UI. The Agent SDK and
  `claude -p` run a shorter system prompt and fewer tools, so their results do not describe
  Claude Code as people use it.
- Measure accuracy as well as cost. A passing suite shows no regression on those cases, not on
  every input; include correctness, coverage and negative-control cases.
- Harnesses, fixtures and study records live in the eval repository, never in this one.
- For review prompts, the frozen clean-versus-slop testbed (`~/work/slop-testbed` with its answer
  key in `~/work/agent-scripts/`) is the existing eval suite; reuse it.

## Specs are the user's

`capture` generates or edits `spec.md`; `plan`, `refine` and the reviews read it. The person can
edit it at any time, and the spec as written is the ground truth. Evals of these skills score
faithfulness and respect for the person's edits, never whether the skill's own spec is right:

- **Writers:** every section the resolved template requires is present; each criterion's
  provenance is marked (the user's words untagged, `[paraphrase]` or `[inferred]` otherwise);
  the saved spec is offered for editing; a user-edited spec is never silently overwritten.
- **Readers:** the frozen input is a real, possibly hand-edited spec, and the output cites it as
  written, including the person's edits. A trim that makes the skill skip edited sections fails.

## Shipping a kept change

Apply the change to the canonical file, run `./scripts/sync-codex.sh`, and add a CHANGELOG entry
under Unreleased (update flow-next.dev only when behaviour or public guidance changes). No
version bump per change; releases are batched ([releasing.md](releasing.md)). To try a change
locally before a release, re-run `./scripts/install-cursor.sh` or `install-codex.sh`.

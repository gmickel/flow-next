# Spec

## Writing

Before writing under `.flow/specs/`, check existing specs across branches with one git command and compare matches by reading. Use `templates/spec.md` beside the router unless the repo has a root `SPEC.md`, which wins. Read `STRATEGY.md` when present and turn any conflict with its direction into an open question.

When intent cannot yet be stated as criteria, draft the spec with its open questions as the decisions and settle those first. Split only by independently shippable outcome, not by size. Tag any requirement the person did not state as `[inferred]`, and keep requirement IDs append-only: a changed requirement gets a new ID.

Each open question names its owner role; leave other roles' questions open and speak to product owners in plain language. When running something settles a technical unknown, run it and record the result under `## Decision Context` instead. A spec changing more than one repo lists each in frontmatter, and each repo gets its own branch and PR linked from the spec.

End every spec write with a compact visual digest leading with `[inferred]` items. Have another model review the spec only when asked, when design risk is high, or before sharing it with other people; it is not a default step.

## Handover

Deliver the spec by the team's stated convention; a team that approves specs by PR gets a spec-only PR. With no convention recorded, an attended run asks and offers only what this session can do. A product owner's session ends at handover; someone who cannot push hands it over on the tracker issue or as a local file, not a PR.

## Building

Settle open questions with their owners, build against the criteria, and commit the spec on the same branch as the code. For a spec from a tracker issue, snapshot the issue into the spec file at build start and save the tracker read's `snapshot` value in frontmatter. If a later read returns a different value, the issue changed: ask the person, and never merge the two.

# Spec

## Writing

A spec's id is its title as a short slug, prefixed with the tracker key when it comes from an issue, and never a number; the file is `<id>.md`. Before writing, check existing specs with one git command across branches and both spec folders, and compare matches by reading. An id is used once: on a clash, add a distinguishing word.

Finished specs live in `.flow/specs/`; a spec waiting on the default branch for its work lives in `.flow/specs/open/`. Write a spec that ships in the same PR as its work straight to `.flow/specs/`, so nothing ever moves. Put a spec in `open/` only when it reaches the default branch before its work is complete (a spec-only PR, a backlog, a goal's parent). Read open or finished from the default branch, never from a feature branch, and refer to a spec by id, not by path.

Use `templates/spec.md` beside the router unless the repo has a root `SPEC.md`, which wins. Read `STRATEGY.md` and any repo glossary (whatever its name) when present, turning any conflict with direction or terms into an open question. When a term is first settled with no glossary, offer to create a root `GLOSSARY.md` holding that one term—only on first need with the person's yes. Read existing decision files and record new decisions in the repo's form; otherwise `## Decision Context` is the record, and do not create a decisions directory.

When intent cannot yet be stated as criteria, draft the spec with its open questions as the decisions and settle those first. Split only by independently shippable outcome, not by size. Tag any requirement the person did not state as `[inferred]`, and keep requirement IDs append-only: a changed requirement gets a new ID.

Each open question names its owner role; leave other roles' questions open and speak to product owners in plain language. When running something settles a technical unknown, run it and record the result under `## Decision Context` instead. A spec changing more than one repo lists each in frontmatter, and each repo gets its own branch and PR linked from the spec.

End every spec write with a compact visual digest leading with `[inferred]` items. Have another model review the spec only when asked, when design risk is high, or before sharing it with other people; it is not a default step.

## Handover

Deliver the spec by the team's stated convention; a team that approves specs by PR gets a spec-only PR. With no convention recorded, an attended run asks and offers only what this session can do. A product owner's session ends at handover; someone who cannot push hands it over on the tracker issue or as a local file, not a PR.

## Building

Settle open questions with their owners, build against the criteria, and commit the spec on the same branch as the code. For a spec from a tracker issue, snapshot the issue into the spec file at build start and save the tracker read's `snapshot` value in frontmatter. If a later read returns a different value, the issue changed: ask the person, and never merge the two.

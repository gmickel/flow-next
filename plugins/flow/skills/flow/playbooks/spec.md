# Spec

## Writing

A spec's id is its title as a short slug, prefixed with the tracker key when it comes from an issue, and never a number; the file is `<id>.md`. Before writing, check existing specs with one git command across branches and every spec folder, and compare matches by reading. An id is used once: on a clash, add a distinguishing word.

Finished specs live in `.flow/specs/`; a spec waiting on the default branch for its work lives in `.flow/specs/open/`. Write a spec that ships in the same PR as its work straight to `.flow/specs/`, so nothing ever moves. Put a spec in `open/` only when it reaches the default branch before its work is complete (a spec-only PR, a backlog, a goal's parent). A spec someone wants kept but not started yet (a captured idea, a draft they have not decided on) goes in `.flow/specs/parked/` instead: nothing picks it up or asks about it there, and it may be as short as a title and a paragraph. A person, or an attended session they ask, moves it to `open/` to queue it, with `git mv` and the id unchanged; parking a spec that has a tracker issue also moves the issue out of the ready state. Read which folder a spec is in from the default branch, never from a feature branch, and refer to a spec by id, not by path.

A spec may wait on others with one frontmatter line, `after: [<spec-id>, ...]`, kept on one line. It is ready when every id it names is a finished spec on the default branch's latest remote state; an id still in `open/` or `parked/`, or only on an unmerged branch, is not finished, and an id that exists nowhere is unknown and is reported. `grep -H '^after:' .flow/specs/open/*.md` reads every relation, and `tsort` orders them and names a loop (read its messages, not its exit code; order by reading where it is missing). When writing or changing an `after` line, check for a loop and stop on one. Dropping a waiting spec deletes its file and fixes every `after` that names it in the same commit.

Use `templates/spec.md` beside the router unless the repo has a root `SPEC.md`, which wins. Read `STRATEGY.md` and any repo glossary (whatever its name) when present, turning any conflict with direction or terms into an open question. When a term is first settled with no glossary, offer to create a root `GLOSSARY.md` holding that one term—only on first need with the person's yes. Read existing decision files and record new decisions in the repo's form; otherwise `## Decision Context` is the record, and do not create a decisions directory.

When intent cannot yet be stated as criteria, draft the spec with its open questions as the decisions and settle those first. Split only by independently shippable outcome, not by size. Tag any requirement the person did not state as `[inferred]`, and keep requirement IDs append-only: a changed requirement gets a new ID.

Each open question names its owner role; leave other roles' questions open and speak to product owners in plain language. When running something settles a technical unknown, run it and record the result under `## Decision Context` instead. A spec changing more than one repo lists each in frontmatter, and each repo gets its own branch and PR linked from the spec.

End every spec write with a compact visual digest leading with `[inferred]` items. Have another model review the spec only when asked, when design risk is high, or before sharing it with other people; it is not a default step.

## Handover

Deliver the spec by the team's stated convention; a team that approves specs by PR gets a spec-only PR. With no convention recorded, an attended run asks and offers only what this session can do. A product owner's session ends at handover; someone who cannot push hands it over on the tracker issue or as a local file, not a PR.

## Building

Before starting a spec, check its `after`. With a person, say what it waits on and ask; if they say start anyway, remove that id from the line and add one Decision Context line saying who decided and why. Unattended, never start a spec that is not ready: start the first ready spec in `open/` that it waits on instead and say so, or stop with the reason when none can start. An unattended run makes moving the spec out of `open/` its first commit and pushes it at once, so that others can see it has been started. Start on top of another spec's unmerged branch only when a person asks; that PR says so and stays a draft until the first has landed.

Settle open questions with their owners, build against the criteria, and commit the spec on the same branch as the code. For a spec from a tracker issue, snapshot the issue into the spec file at build start and save the tracker read's `snapshot` value in frontmatter. If a later read returns a different value, the issue changed: ask the person, and never merge the two.

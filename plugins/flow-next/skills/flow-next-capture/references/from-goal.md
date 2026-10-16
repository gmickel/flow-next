# capture — from:goal (gated reference)

> Read only when SKILL.md parsed the exact `from:goal` token, which a goal run (`flow --goal`)
> sends. The autofix rules ([autofix-mode.md](autofix-mode.md)) hold too, with the write
> authorized; this file says only what a goal run changes.

## What follows the token

- An open spec id: the goal. Capture mints one child spec for it.
- Anything else (a path, a URL, a tracker issue, pasted text): the source. Capture writes the goal
  spec itself from it.

## The source stands in for the conversation

Wherever workflow.md reads the user's turns, read the source instead, from disk or the invocation
and never from memory of the session: for a goal, the source's own words; for a child, the goal
spec (its criteria, Boundaries, Decision Context, any answers the person wrote, its goal log) and
the gap the goal run stated in this session (the criterion, its last result, the route, the
premise, any probe result). A line is untagged only when it is the source's own words. The
compaction check (§0.4) does not apply, because nothing comes from the transcript.

The duplicate scan (§0.2) never counts the goal itself, or a child already recorded in its goal
log, as a match for a new child; it still counts every other open spec. An earlier capture in
this session (the goal, or another child) is not a repeat for §0.6: only a capture for the same
gap is.

## Writing the goal

The criteria are the bar. Each must be checkable: a command, a test, a benchmark, or a judgment a
named person gives. When none is, exit 2 with `no checkable outcome`, writing nothing. Skip the
spec-count gate (§2.5): the goal run divides the bar into children, so capture never splits a
goal. Leave route recording to the goal run (no `no_plan` write); the goal stays unready.

## Writing a child

One pull request of work. Its Goal & Context names the goal and the criterion it serves; it
carries the goal's Boundaries that apply and the goal's settled decisions in its Decision
Context. Exit 2, naming the reason, when the child would cross a goal Boundary or reopen a settled
decision, when it trips the spec-count tripwire (the goal run mints a smaller one), or when a
duplicate is found (name the matching specs). Route recording is left to the run that builds it,
as for any spec a person wrote.

## Never, under from:goal

Capture never marks a spec ready, never writes glossary terms, and never writes the goal log:
the goal run does what is its own. The closing block omits `Recommended next:`.

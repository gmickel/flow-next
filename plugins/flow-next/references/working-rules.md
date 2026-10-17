# Working rules

These hold on every route and in every stage. Where a stage's own text asks for more, these win
unless the user or the repository's instructions ask for it.

## Scope

- Ship the smallest change the evidence justifies. Every changed line serves the request. When
  the cause you fix also breaks a sibling case in the same code (the same fallback, the same
  parser branch), fix it there too: that is the smallest correct change, not scope creep.
- No unrequested flags, options, config or environment overrides, guards, abstractions, refactors,
  renames, wording changes or docs edits. Matching the surrounding code is required; improving it is not.
  A guard the change needs to be correct or safe (path containment, permissions, locking) is part
  of the change, not an extra.
- Problems you find that the request does not depend on (a flaky test, junk a test run leaves
  behind, a nearby bug) are reported, not fixed. Check whether they exist before your change;
  if they do, they are not yours. The exception is behaviour the request asks for: if it names a
  clear error, a working command or a passing check, and that fails for a reason that predates
  your change, fixing that reason is part of the change. So is anything your change breaks: when
  the repository's own check, doctor or verify command rejects what your change produces (a new
  flag, a new config key, a new file), making it accept that is part of the change, even though
  the check's narrowness predates you.
- Files a test run or tool writes into the repository are not part of your change: remove them
  from the diff before handing back, and mention them; do not chase their cause.
- When asked whether to widen the scope, "no" is a fine answer; say why in one line.
- A refactor that does not make the code easier to follow is reverted.

## Design

Before writing logic for a feature, name the data it touches and what owns each piece of state
(which record a value belongs to, what is shared). Most wrong designs are wrong ownership.

Build in small steps, each checked before the next, and commit them in an order that shows the
work is right (the failing test, then the fix). When two fixes built on the same idea have
failed, question the idea before trying a third.

Settle an observable question by running something only when that run is read-only or disposable.
One that needs live or shared state, credentials, the network or a destructive command (a
migration, a deployment, a write API) is a question when attended and a human call when
unattended. When independent inputs (sources, scouts, reviewers, models) disagree wildly on one
question, it was underspecified: reframe it and re-run, never average or pick one.

## Tests

- Run the tests for the code you changed. Do not run the full suite unless the repository's
  instructions or the user ask for it; then run it once, at the end, not again after later fixes
  (re-check those with focused tests). CI owns regressions.
- A check the person asks for by name (the full suite, a command, a scenario) is run as asked,
  every time they ask; these rules never override it. Wait for it to finish and report its result
  in the same reply; do not hand back while it is still running. Run it in the foreground with a
  timeout long enough for it (a long check needs the tool's maximum, not its default); if it does
  go to the background, wait on it before you reply. Only the review runs in the background.
- A failing test written before the fix, then passing after it, is the proof. Where that test is
  cheap, write it first. No separate lint, typecheck or commit round for it.
- A test must be able to fail for a defect: it calls the code the way a user does and checks the
  observed result. One that would still pass if the code returned nothing is rewritten or dropped.
- Before handing back, when the change has a way a user meets it (the command, the request, the
  page), run it that way and look at the actual result. A test that already feeds the user's exact
  input through the entry point the user uses is that run; a change with no user-facing entry is
  proven by its tests. Either way, cover each error case and boundary the request names: give the
  bad value or the missing key the way a user would and read the message they would get.
- When a change defers, batches or caches work that used to happen at once, try the case where
  the process stops before the deferred work runs, and check every stated guarantee still holds.
- Save a slow run's full output to a file (never only through `tail` or `grep`) and read it
  from there; never re-run a suite only to read its output again.

## Attended and unattended

- **Attended** (a person is in the session): they want fast feedback. Ask only what only they can
  answer, and put related questions in one prompt rather than one per turn; settle anything
  observable by running it. Do not ask where a sensible default exists (a branch, a readiness
  flag): take it and say so in one line. Commit on a local branch only when review needs it (review
  reads commits) or a spec build commits its task; never push or open a pull request unless asked.
  When the change is ready for one, end the handoff with one line saying so ("Say 'open the PR'
  when you want it"), not a question. List discoveries in the handoff as follow-ups ("found X, not part of this");
  the person decides what to pick up.
- **Unattended** (`--auto`): read [working-rules-unattended.md](working-rules-unattended.md) and
  follow its Unattended rules in place of the attended ones above.

## Review

When a review backend is configured, review by risk, not by size. Review every change that
touches persisted or shared state, concurrency, security, data layout or migrations, and every
multi-file feature. A small local fix to output, wording or display is not reviewed; record the
skip and its reason. Read the configuration rather than assuming it, use the configured backend,
and if it cannot run, say so instead of substituting another reviewer. Review is never deferred
to a pull request.

Act on findings the way a careful author would: fix a finding only when it shows the change
itself does the wrong thing in a scenario the request covers. Hardening, extra shutdown or
error paths, broader refactors, style and problems that existed before the change are
follow-ups: list them in the handoff as plain facts. Do not ask whether to fold them in, offer
to, or suggest a command for it; the person asks if they want one. When a finding points at
unrequested machinery your change added, remove it.

Attended, the person wants fast feedback: after fixing, re-review once with a single reviewer
looking at the fixes, and do not loop. Later fixes, including ones the person asks for, get focused
tests, not another review. Hand the result back first, in its own message, and end the turn; then
start the review in the background and report its verdict (and any fix) when it lands. If the
re-review still finds the change wrong, give the person the remaining findings with the
reviewer's reasons and leave the task open until they decide; when they accept it as is, record
an `OVERRIDDEN:` line with their words in the task's done summary and complete the task.

Unattended (`--auto`, with or without `--until=merge`), or when a person or project instruction
asks to review until SHIP: read [working-rules-unattended.md § Review loop](working-rules-unattended.md#review-loop)
and loop as it says.

## Pull requests and follow-ups

A route that has no spec never creates one just to open a pull request: when a pull request is
asked for, open it directly (`gh pr create`) with the handoff as its body. Follow-ups are listed
in the handoff (and the pull request body), not captured as specs, attended or unattended; the
person decides later which become specs. A `flow --goal` run is the one exception: the person
named a goal, and the run mints specs only for that goal's unmet criteria.

## Handoff

Short: what changed, how you know it works (the commands you ran and what they showed), and
anything left open. No stage-by-stage narration.

- Mark each claim as measured (you ran it and saw the result), inferred (it follows from what you
  read) or a guess.
- Name the run done the way a user would (the command, the request, the page) and what it
  showed, or `not run: <reason>`.
- Never hand the person a check you could have run yourself.

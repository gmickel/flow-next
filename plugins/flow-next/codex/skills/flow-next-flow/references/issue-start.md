# Starting from a tracker issue (gated reference)

> Read from auto.md only when the run parsed `--from-issue <key|url>`. It runs before auto.md's
> Phase 1 and hands back to it with one named spec. auto.md's verdict contract, Forbidden list,
> hop loop, strikes and landing rules still hold.

The person's consent is the board move: an issue someone put into `tracker.readyState` may be
captured and built without anyone capturing it first, as long as it is clear enough to build
unattended. When it is not, the run asks on the issue and moves it out of the ready state; the
person answers there and moves it back, which starts the next run. One run per issue at a time is
the driver's responsibility.

auto.md's parse has already refused a missing issue and `--from-issue` combined with a spec id,
`--goal` or `--backlog`. `--explain` runs the reads below (consent, resolve, route, bar) and prints
what the run would do; it posts, captures, commits and moves nothing.

## 1. Start guard and consent

Run auto.md's snapshot fence with `PILOT_SPEC` empty and apply its guards (a dirty tree stops the
run). Then, before any write:

- `"$FLOWCTL" sync active --json` reads `active: true`, and `tracker.readyState` is set.
- `"$FLOWCTL" tracker wire list-open --json` lists the issue: match its `identifier` or `url`
  against the key or URL given. A Jira row has no `url`: a Jira URL counts only when its host is
  the host of `tracker.perTracker.baseUrl`, and then its key is matched; a URL from another site
  stops `NEEDS_HUMAN` with `issue URL is not on <baseUrl>`. That row
  is the consent read (the exact ready lane) and supplies
  the locator, `{"durable": <id>, "display": <identifier>}`. A truncated listing never counts as
  absent.
- `"$FLOWCTL" tracker wire read --locator "$LOCATOR" --json` and
  `"$FLOWCTL" tracker wire comment-list --locator "$LOCATOR" --json` give the body and comments;
  a comment listing with `truncated: true` counts as a failed read.

Any of these false or failing stops `NEEDS_HUMAN` with the reason or transport error, before any
write; an issue not in the ready lane is `issue <key> is not in <readyState>`.

## 2. Resolve an existing spec

A spec is linked when its JSON's `tracker.id` is the issue's durable id.
`"$FLOWCTL" specs --refs --fetch --tracker-id "<durable id>" --json` fetches origin and lists every
linked spec with where its link is: `checkout: true` for the checkout's `.flow/specs/*.json`,
committed or not, and `refs` for each local or remote-tracking branch whose JSON carries it (a spec
already on the default branch and a link added by a JSON-only change count). A `fetch_error`, or the
command failing (a spec JSON it cannot read), stops `NEEDS_HUMAN`, never a capture.

- Two or more linked specs stop `NEEDS_HUMAN` naming them. None: continue below.
- One: bring it into the checkout. The checkout holds the link: stay. `origin/<default>` holds it:
  on the default branch fast-forward (`git merge --ff-only origin/<default>`); a checkout on
  another branch stops `NEEDS_HUMAN`. Otherwise switch to the branch it lists by its short
  name (`git switch <name>` for `refs/remotes/origin/<name>`, which tracks it), never the
  remote ref itself. Then set `PILOT_SPEC` and continue with auto.md exactly as
  `flow --auto <spec-id>` would, capturing nothing.
- A spec an issue start captured is finished first. When its spec file has no commit yet
  (`git log -1 -- .flow/specs/<spec-id>.md` prints nothing), its capture was interrupted, whoever
  wrote it: finish step 5 from where it stopped (its checks, `spec ready`, the branch, the capture
  commit and the push). When its spec file's latest commit is step 5's capture commit and its
  branch is not on origin yet, push it as step 5 does. Either way it keeps step 5's design review
  before any work hop. Any other linked spec runs exactly as a person left it.

## 3. Read the source

The source is the issue body and its comments. When a comment carries a `flow-next:question`
marker from an earlier run, the person moving the issue back into the ready state, with a comment
after that marker, is the answer: use the body plus every comment after the latest such marker,
and treat that question as settled. With no comment after it the question is still open (a run
stopped before it moved the issue out, or the answer is an edit to the body): the source is the
body.

## 4. Route and the bar

Classify the issue with [route-matrix.md](route-matrix.md) before writing anything:

| Reads as | Captured as |
|---|---|
| A feature or clear change | An ordinary spec |
| A reported defect | "The reported behaviour stops happening", checked by a failing test, as an R-ID; work's defect route then loads by itself |
| A refactor meant to keep behaviour | A pinned characterization of current behaviour as the R-ID |
| A slowness to move once | A measured baseline and its target as the R-ID |
| A tiny change | A short spec (the issue needs a spec linked to it) |

A non-build issue (a question to answer, an artifact to explain, a safety question about a diff, a
design fork, a goal or epic, a hill climb) is refused (step 6), naming the route that fits.

The bar for an unattended build: small and fully known, one cohesive pull request, no open
question, no decision an ADR would record, no request for a plan or task breakdown, not a goal or
epic, and every acceptance criterion testable and traceable to the issue. A stricter bar the
repository's AGENTS.md states wins. An issue that misses it is refused (step 6) with the
questions that would close the gap.

## 5. Capture, commit, review

Invoke `$flow-next-capture from:issue <identifier> --no-plan`, passing the source from step 3 and the route.
Capture exits 2 with a question when a criterion would have to be invented: refuse (step 6) with
it. Its exit 2 for a duplicate open spec stops `NEEDS_HUMAN` naming that spec.

After a successful capture:

- `"$FLOWCTL" show <spec-id> --json` must show `tracker.id` equal to the issue's durable id
  (a link collision stops `NEEDS_HUMAN` naming the holder) and `no_plan: true`.
- `"$FLOWCTL" spec ready <spec-id> --json`, recorded in the run's `Decisions:` list as readiness
  taken from the board move.
- Create the spec's `branch_name` from the default branch's remote head, commit only the spec's
  `.flow/` files as `chore(flow): capture <spec-id> from <identifier>`, and
  `git push -u origin <branch_name>`. A failed push stops `NEEDS_HUMAN`; no work is dispatched. The
  spec then reaches the default branch with the pull request that builds it.

Set `PILOT_SPEC` and rerun auto.md's snapshot fence for it, then continue with auto.md's phases.
Under `--tick` the capture is the hop: end `ADVANCED`, `stage=capture`.

**Design review before work.** The captured spec gets a design review against the issue before any
work hop: it counts as an explicit request to review the spec's design (auto.md Arguments), so
CLASSIFY routes to `plan-review` first, with the focus that the spec must say what the issue it
quotes says. A spec an issue start captured that step 2 resolves with no tasks and a plan review
still `unknown` gets the same review. Only a sentence in the repository's AGENTS.md turning this review off for specs a run
captured skips it; record that skip with the sentence. A run that dispatched work on such a spec
without the review or that sentence has broken this.

**Implementation review on every work hop.** Nobody wrote the spec and nobody reads the code before
an unattended merge, so every work hop of an issue start, on a spec step 2 resolved or step 5
captured, runs implementation review on the configured backend: the working rules' risk rule never
skips it here. auto.md's work dispatch says so to work. With no backend configured, work's skip and
its note stand.

## 6. Refuse: ask on the issue

Write the questions to a mode `0600` file: each one names what is unclear, the options when they
are known, and who decides (`*(owner: <role>)*`); end with "Answer here or edit the issue, then
move it back to <readyState>." For a non-build issue, say which route fits and how to run it. Post:

```bash
"$FLOWCTL" tracker wire question --locator "$LOCATOR" \
  --subject-id "<durable id>" --blocked-stage capture \
  --reason-code "<not-buildable | not-a-build>" --question-slug "<short topic slug>" \
  --reply-settles --body-file "<file>" --json
"$FLOWCTL" tracker wire unready --locator "$LOCATOR" --json
```

The slug names the topic, so the same question asked again dedupes and a new one posts.
`--reply-settles` makes a comment after the latest matching question settle that round, as step 3
reads it: a follow-up on the same topic after a plain reply posts a new round, and a rerun of a
round nobody replied to dedupes. No spec is
written. A failed post stops `NEEDS_HUMAN`. A failed `unready` (for example `backlog_slot`) leaves
the posted question standing; name the failure in the reason.

```text
PILOT_VERDICT=ASKED spec=<identifier> stage=capture reason="parked behind <n> question(s) on <identifier>: <one line>"
```

No strike is recorded for a refusal.

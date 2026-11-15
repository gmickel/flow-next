# Unattended start from a tracker issue: flow --from-issue

## Goal & Context

<!-- Source: 35% user / 45% [paraphrase] / 20% [inferred] -->

A team that runs flow unattended from its tracker board wants an issue filed straight into the ready state ("there's a bug here and here") to be built without someone capturing a spec first. Today `flow --auto` builds only a captured, ready spec: the ready flag is its consent boundary and nothing captures upstream of it; backlog mode only reports a "needs capture" gap; goal mode captures unattended but is built for multi-spec goals with an integration branch. [paraphrase]

"the factory is not going to work if someone has to manually capture everything."

The outcome: "an unattended flow that starts from a tracker issue, captures a linked no-plan spec tracker-first under the repository's stated bar, asks its questions on the issue when the issue is not clear enough, and otherwise builds and lands in the same run."

The surface is driver-neutral: a webhook daemon, a cron job, CI or a host loop can invoke it. How any particular driver routes issues is out of scope. [paraphrase]

## Architecture & Data Models

- **New entry: `flow --auto --from-issue <key|url> [--until=merge]`**, loaded from its own gated reference in the flow skill, as `--goal` and backlog mode are. Attended flow and the ready, backlog and goal modes never read it. [paraphrase]
- **Consent.** A person moving the issue into `tracker.readyState` is the consent to capture and build it; `--until=merge` on the current invocation is the consent to land, as today. This follows STRATEGY's "Consent comes from a person": the mode names the explicit act it rests on, a board move. [paraphrase]
- **The run in order:** [paraphrase]
  1. **Resolve.** After a fetch, look for a spec linked to the issue in the checkout and on remote branches (`flowctl specs --refs` already reports each spec's tracker link). Found: continue exactly as `flow --auto <spec-id>`.
  2. **Route on content.** Read the issue and classify it with flow's route matrix before writing anything: a feature or clear change, a defect, a refactor meant to keep behaviour, a one-off slowness, a tiny change, or not a build.
  3. **Capture under the bar.** `flow-next-capture from:issue <issue>` writes one linked no-plan spec, or refuses with questions.
  4. **Review the spec.** Plan-review checks the captured spec against the issue text.
  5. **Build.** Continue from `flow --auto`'s classification onwards with the new spec, so every existing gate (work's defect route, impl-review, QA, make-pr, land) applies unchanged.
- **The bar** is guidance in the reference, not a config key. An issue suits an unattended build when it is small and fully known, fits one cohesive pull request, has no open question and no decision an ADR would record, asks for no plan or task breakdown, is not a goal or epic, and every acceptance criterion it implies is testable and traceable to the issue. A repository may state a stricter bar in its AGENTS.md; the stricter one wins. [inferred]
- **Capture `from:issue`** is a sibling of `from:goal`: unattended, write authorized by the run, the issue body and its comments standing in for the conversation. A line is untagged only when it is the issue's own words; acceptance criteria are quoted or `[paraphrase]`, never `[inferred]`. A criterion capture would have to invent becomes a question instead. [inferred]
- **Route-shaped specs.** A defect's R-ID is that the reported behaviour stops happening, checked by a failing test, so work's defect route loads by itself; a refactor's R-ID is a pinned characterization of current behaviour; a slowness's R-ID is a measured baseline and target; a tiny change still gets a short spec, because the issue start needs a spec linked to the issue. [paraphrase]
- **Refusal (the question valve).** An issue that fails the bar, or a non-build issue, gets its questions posted on the issue through the existing `tracker wire question` with the issue as subject, and no spec is written. The run then moves the issue out of the ready state with `tracker wire unready` (sibling spec). A non-build issue's comment names the route that fits it. [paraphrase]
- **Re-entry.** A person answers in a plain comment or edits the issue, then moves it back to the ready state. The next run treats that return as the answer and reads the issue body plus every comment after the question as its source. Nobody has to type an answer marker. [paraphrase]

## API Contracts

- Invocation: `/flow-next:flow --auto --from-issue <issue key or URL> [--until=merge] [--review=<backend>] [--tick] [--explain]`. [inferred]
- Terminal line: auto mode's existing grammar, plus `ASKED` for a refusal, as backlog mode uses it: [inferred]

```text
PILOT_VERDICT=ASKED spec=<issue key> stage=capture reason="parked behind <n> open question(s): <one line>"
```

- A capture or a refusal is stage `capture`; once a spec exists, `spec=` names it and later stages use their existing names. [inferred]

## Edge Cases & Constraints

- **Not ready on a live read**, bridge inactive or `tracker.readyState` unset: `NEEDS_HUMAN` before any write. [inferred]
- **Two specs linked to one issue** (local or on remote branches): `NEEDS_HUMAN` naming both. [inferred]
- **A spec linked by a person meanwhile:** resolve finds it and the run continues as `flow --auto <spec-id>`; the readiness and strike rules for that spec apply as today. [inferred]
- **Two deliveries for one issue:** one run per issue at a time is the driver's responsibility, stated as in goal mode; a second run on the same checkout is refused by the existing one-issue-one-spec link rule. [inferred]
- **A half-failed capture:** the spec commit is pushed on the spec's branch immediately after capture, before work, so a later run's resolve finds it; a run that died before the push leaves at most an uncommitted local spec, which resolve finds in the same checkout. [inferred]
- **The spec commit** travels on the spec branch and lands with its pull request; nothing is pushed to the default branch. [inferred]
- **A struck spec redelivered:** `NEEDS_HUMAN` naming `flowctl pilot strikes clear`; strikes are unchanged. [inferred]
- **The move out of the ready state fails** (for example no `backlog` slot on Jira): the question is already posted; the verdict says the move failed and the issue stays where it was. [inferred]
- **The work turns out bigger or less known while it runs:** the existing stop applies; the run never grows the pull request. [inferred]

## Acceptance Criteria

- **R1:** `flow --auto --from-issue <issue>` starts only when the tracker bridge is active, `tracker.readyState` is set and a live read shows the issue in that state. Errors: any of those false → `NEEDS_HUMAN` before any write; the issue cannot be read → `NEEDS_HUMAN` with the transport error. [inferred]
- **R2:** When a spec in the checkout or on a fetched remote branch is linked to the issue, the run continues exactly as `flow --auto <spec-id>` would and captures nothing. Errors: two linked specs → `NEEDS_HUMAN` naming both; a failed fetch → `NEEDS_HUMAN`, never a capture. [inferred]
- **R3:** Before writing, the run routes the issue on its content with flow's route matrix: a defect is captured with "the reported behaviour stops happening" as an R-ID checked by a failing test, a refactor with a pinned characterization, a one-off slowness with a measured baseline and target, a tiny change as a short spec, and a feature or clear change as an ordinary spec. A non-build issue (a question, an artifact to explain, a safety question, a design fork, a goal, a hill climb) is refused per R8 with the fitting route named. No error surface beyond R8. [paraphrase]
- **R4:** The run applies the default bar above, and a stricter bar stated in the repository's AGENTS.md wins. An issue that fails either is refused per R8. No error surface beyond R8. [inferred]
- **R5:** `flow-next-capture from:issue <issue>` writes one spec from the issue body and comments, leaving only the issue's own words untagged, with every acceptance criterion quoted or `[paraphrase]` and none `[inferred]`. Errors: a criterion that would need inventing → exit 2 with the question; a duplicate open spec → exit 2 naming it; a split proposal → exit 2 (refused, never split). [inferred]
- **R6:** The captured spec is linked to the issue in either id mode, recorded no-plan, marked ready by the run (logged in its `Decisions:` list), committed and pushed on its own branch before work starts. Errors: a link collision → `NEEDS_HUMAN` naming the holder; a failed push → `NEEDS_HUMAN`, no work dispatched. [inferred]
- **R7:** A spec the run captured gets a plan-review against the issue text before work by default, under the existing plan-review rules and verdicts; a repository turns it off with a sentence in its AGENTS.md. Errors: no review backend configured → `NEEDS_HUMAN`, as for any selected review gate. [paraphrase]
- **R8:** A refusal posts the questions on the issue through `tracker wire question` (no spec written), moves the issue out of the ready state with `tracker wire unready`, and ends `ASKED`. Errors: no reachable transport → `NEEDS_HUMAN`; the unready move fails → the verdict names the failure and the posted question stands. [paraphrase]
- **R9:** When an issue with an open question from an earlier run is back in the ready state, the run treats the question as answered and uses the issue body plus every comment after the question as its source. A second question round dedupes by the existing question id. No error surface beyond R1 and R8. [paraphrase]
- **R10:** Attended flow, the ready, backlog and goal modes, `--until=merge` consent and the strikes ledger behave as in 9.10.0 when `--from-issue` is absent. No error surface. [paraphrase]

Tests pin the parse, the verdict grammar, the consent stop, the refusal path and the unchanged modes as contracts (G2); a live check against a Linear workspace runs before the release. Docs: the flow and capture pages, tracker sync, the autonomy guide, and flow-next.dev. [inferred]

## Boundaries

- No driver-specific routing; which issues a driver sends here is that driver's choice. [paraphrase]
- No capture outside `--from-issue`: ready and backlog modes keep "never author a spec". [inferred]
- No spec stub on refusal, and no spec written for a non-build issue. [inferred]
- No push to the default branch; the spec lands with its pull request. [inferred]
- No config key for the bar. [inferred]
- No comment webhook or comment-only re-trigger; a return to the ready state is the signal. [paraphrase]

## Decision Context

- **Built in flow-next, not in a driver.** Capture's provenance tags, the tracker-first link, the question valve, `readyState` and the strikes ledger already live here; a driver that captured on its own would duplicate them, and every other driver gets the feature too. [inferred]
- **A new flag, not goal mode or backlog mode.** Goal mode brings an integration branch, children and a goal log; backlog mode sweeps the board and its never-author rule is its point. An explicit flag keeps the consent change visible in the command. [inferred]
- **Spec review on by default.** Without it nothing independent checks the spec against the issue before an unattended merge: impl-review checks the diff against the spec, never the spec against the issue. Gordon chose on by default. [paraphrase]
- **No inferred criteria.** This is the check that stops a mostly invented spec from being built and merged with nobody reading it; inferred technical context stays allowed. [inferred]
- **Return to the ready state as the answer.** People do not type answer markers in a tracker UI, and a webhook already fires on that move; Gordon chose it over a comment trigger. [paraphrase]
- **Resolve through `specs --refs`, no new read verb.** It already reports each spec's tracker link across fetched branches. [inferred]
- **Sibling specs:** fn-324 "Unready a tracker issue and link named issues in any id mode" (dependency). fn-314 (attended triage of open issues) is separate: it grooms many issues with a person; this builds one promoted issue without one. [inferred]

## Strategy Alignment

- Autonomous mode: extends the unattended path while keeping promotion a person's board act and landing on current consent. [strategy:Autonomous mode]

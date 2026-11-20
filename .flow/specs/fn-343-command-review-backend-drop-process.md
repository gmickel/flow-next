# Command review backend: drop process-tree management, wrapper owns its child

## Goal & Context

<!-- Source: 10% user / 50% [paraphrase] / 40% [inferred] -->

fn-339 made a command review backend stop its wrapper's whole process tree on timeout. To do that it starts the wrapper in its own session, which cut the wrapper off from Ctrl-C. fn-342 then added interrupt handling to get that back, and moved fan-out draws onto background threads. Two cross-family audits in a row found new defects in exactly that code: reviewers of every other backend left running after an interrupt, a wait on Windows that Ctrl-C cannot break, a session lost when a fan-out is interrupted, cleanup races. Each fix has added more moving parts than it removed.

None of this is released. 9.17.0 ran the command backend the way every other CLI backend runs: one child process in flowctl's own process group, killed directly on timeout, reached by Ctrl-C because it shares the terminal. That behaviour had no reported problem. This spec goes back to it and states the one real limit in the docs, so 9.18.0 can ship without the machinery.

The maintainer's standing rules decide this: no machinery where a sentence will do, nothing released that is broken or untested, and every added mechanism costs every run.

## Architecture & Data Models

- A command review backend runs its argv as one child in flowctl's own process group, exactly as in 9.17.0. On timeout flowctl stops that child. Ctrl-C reaches it through the terminal like any other reviewer. [paraphrase]
- Fan-out draws run as they did in 9.17.0, on the same executor for every backend. No background threads, no cancellation registry, no bounded abandonment. [paraphrase]
- The wrapper owns the lifetime of anything it starts. The request already carries the timeout, and the documented example passes it to the CLI it runs. [paraphrase]

## Edge Cases & Constraints

- Everything else from fn-339 and fn-342 stays: the criteria link-as-file error and its probe from the repository root, the receipt parser fix, the bare `command` refusal, the error text that does not print the program path, same-label session fallback, strict spec parsing in the validate and deep passes, the setup and plan messages, the Antigravity setup label, the pinned ladder tests. [paraphrase]
- An oversized response fails the round as it did in 9.17.0. [inferred]
- The removal is checked against 9.17.0: for the command dispatch and the fan-out scheduler, the code after this change should differ from the 9.17.0 tag only where a kept fix requires it. [inferred]

## Acceptance Criteria

- **R1:** The command review backend no longer starts its wrapper in a separate session and no longer manages a process tree: no tree-stop helper, no interrupt registry, no background-thread fan-out, no interrupt wait bounds. For the command dispatch path and the fan-out scheduler, a diff against tag `flow-next-v9.17.0` shows only the kept fixes listed above. [paraphrase]
  Errors: a kept fix that cannot stand without part of the removed code is reported, and that part is kept with its reason.
- **R2:** Ctrl-C during a single command review and during a fan-out behaves as it did in 9.17.0 for every backend: the reviewers receive the interrupt with flowctl, and flowctl exits without leaving a reviewer it started in the foreground process group. A test or a recorded live run shows this for the command backend and for one other CLI backend. [paraphrase]
  Errors: no error surface beyond the interrupt itself.
- **R3:** The docs for the command backend, and the mirror, say plainly that flowctl stops only the program it started, that a wrapper must pass the request's timeout to whatever it runs and must not detach it, and that Ctrl-C reaches the wrapper's children only while they stay in the same process group. The earlier notes about stopping process trees, detached helpers and Windows tree limits are removed. [paraphrase]
  Errors: no error surface.
- **R4:** The documented Antigravity review wrapper takes the `agy` program from one explicit absolute path the user sets (a constant at the top of the wrapper or one environment variable), and does no `PATH` lookup at all. [paraphrase]
  Errors: the path unset, not absolute, or not executable → the wrapper fails with a clear message and no review runs.
- **R5:** A draw's pending row records its command label when the draw is dispatched, so a fan-out that is interrupted and then finalized keeps a same-label survivor's session and never writes a receipt with an empty label or a bare `command` spec. [paraphrase]
  Errors: a different-label survivor is still refused.
- **R6:** A stored legacy backend string that names a model the Copilot ladder no longer lists, such as `copilot:gpt-5.5-high`, resolves as it did in 9.17.0. The retired ids go back into the Copilot ladder's tail, which is the smallest change that restores it. [paraphrase]
  Errors: no error surface beyond the existing ladder step-down.
- **R7:** fn-339's third criterion and fn-342's third and fourth criteria are marked withdrawn in those specs with a pointer to this one, and the changelog's Unreleased section no longer claims the process-tree behaviour. [inferred]
  Errors: no error surface.
- **R8:** The full suite passes on Linux, macOS and Windows, and tests that existed only to cover removed code are removed with it. [paraphrase]
  Errors: no error surface.

## Boundaries

- No new mechanism of any kind: no flowctl verb, config key, stage, receipt field, thread, registry or lock. [paraphrase]
- No check of the criteria index before parsing on every review; a link whose target is itself named like a criterion is too contrived to pay for on every run. [inferred]
- No pruning of retired Copilot ids in this release. [inferred]
- No change to the Cursor ladder or to the head of the Copilot ladder. [inferred]

## Decision Context

Stopping a wrapper's process tree was a follow-up nicety, not a reported problem. Its cost turned out to be an isolated session, hand-built interrupt forwarding, threading changes that touched every backend, and platform-specific cleanup, with new defects found in each audit. The alternative is one sentence in the docs telling wrapper authors to pass the timeout on. Removing the mechanism also removes the findings about it: the orphaned reviewers, the Windows wait, the cleanup races.

The stricter checks suggested for the wrapper's `PATH` lookup are answered by not looking anything up. Pruning retired Copilot ids broke the decoding of stored legacy strings; putting them back costs nothing on a healthy ladder.

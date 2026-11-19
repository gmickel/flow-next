# Command review backend for other model families

## Goal & Context

<!-- Source: 5% user / 70% [paraphrase] / 25% [inferred] -->

GitHub issue #592. Reviews run on a fixed set of backends: codex, copilot, cursor, claude and host. Someone who wants a third model family next to GPT and Claude (Gemini through its own CLI, Kimi or DeepSeek through another) has two routes today, and both have a problem. Pinning the model on copilot or cursor needs one more subscription and does not reach every model. Running a provider behind the review execution URL requires that provider to run the requested backend and model, so answering a `codex` request with another model breaks the contract and the receipt says `codex` although something else ran.

The ask is one generic seam instead of one more fixed backend per vendor, because the model list changes every few weeks: a named command in config that flowctl runs to get the reviewer's answer.

`review.backend` is planned to go at some point, with no date. This spec builds on the path that exists today and does not wait for that. [paraphrase]

The unattended failure this prevents: a receipt that names a backend and model that did not run.

## Architecture & Data Models

- One more backend name, `command`, selected with a label: `command:<label>`. The label names an entry in config that holds an argv. [paraphrase]
- It is a second transport for the contract the review execution URL already has. flowctl keeps prompts, rounds, the panel, verdict parsing and receipts; only inference crosses to the command. [paraphrase]
- The command backend runs through the same review runner as every other CLI backend, so the same rule, steps and panel apply. [inferred]
- The wrapper owns read-only access and the model, as the HTTP provider does today. [paraphrase]

## API Contracts

Config:

```json
"review": {
  "commands": {
    "gemini": ["~/bin/review-gemini"],
    "kimi": ["~/bin/review-opencode", "openrouter/moonshotai/kimi-k3.1-pro"]
  }
}
```

- Selection: `review.backend command:gemini`, `--review=command:kimi`, or a per-task or per-spec pin, wherever a backend name is accepted today. [paraphrase]
- flowctl runs the configured argv directly, with no shell and no interpolation; a leading `~` in the first element expands to the home directory. [paraphrase]
- Standard input carries the same JSON request the review execution URL receives (prompt, model, effort, repository path, session id, resume-only, permission mode, timeout, request id). Standard output carries the same JSON response (output, stderr, exit code, session id, resume-failed, observed model). [paraphrase]
- The receipt records the backend as `command`, the label, and the observed model the command reported. [paraphrase]

## Edge Cases & Constraints

- A command that exits non-zero, times out, or prints anything that is not the response shape gives no verdict; the round is refunded and the attempt recorded like any other transport failure. [paraphrase]
- flowctl cannot enforce that a wrapper is read-only. The docs say the wrapper owns it, as with the HTTP provider. [paraphrase]
- A command that reports no session id cannot be resumed; a re-review then starts fresh with the prior findings supplied, as other backends do when resume fails. [inferred]
- The model family behind a command is unknown to flowctl, so the same-family notice is not computed for it; the receipt's observed model is the record. [inferred]
- Model and effort in the request are what the user pinned, or empty; flowctl has no ladder or registry for a command backend. [inferred]
- The config schema, setup, the review skills, the docs and every installed mirror accept and describe the new backend together; a backend that works on one harness only does not ship. [inferred]

## Acceptance Criteria

- **R1:** With a labelled command configured, `command:<label>` is accepted wherever a review backend is named (config, the `--review` flag, per-spec and per-task pins, the environment override), and implementation, plan and completion reviews run through it. [paraphrase]
  Errors: an unknown label, a bare `command` with no label, or an entry that is not a non-empty array of non-empty strings fails before dispatch, naming the label and the config key; no review round is consumed.
- **R2:** flowctl runs the argv without a shell, writes the request to standard input and reads the response from standard output, in the review execution URL's request and response shapes. [paraphrase]
  Errors: executable not found, non-zero exit, timeout, oversized or malformed response → no verdict, the round refunded, the failure recorded with its reason; the command's raw output is never treated as a verdict.
- **R3:** The receipt for a command review names `command`, the label and the observed model; it never names another backend. [paraphrase]
  Errors: a response with no observed model records the model as not reported.
- **R4:** A re-review resumes the session the command returned; when the command reports that resume failed or returned no session, the re-review runs fresh with prior findings supplied. [paraphrase]
  Errors: no error surface beyond R2.
- **R5:** With no command configured, nothing changes for any existing backend. [paraphrase]
  Errors: no error surface.
- **R6:** The docs carry a working example wrapper and state that the wrapper owns read-only access and the model. The config schema describes `review.commands`. [inferred]
  Errors: no error surface beyond documentation.
- **R7:** A live review through one real third-family CLI wrapper reaches a verdict and a correct receipt before release. [inferred]
  Errors: if no third-family CLI can be exercised, the release notes say the path was tested with a stand-in only.

## Boundaries

- No first-class `gemini`, `opencode` or other vendor backend. [paraphrase]
- No model ladder, registry or availability check for command backends. [inferred]
- Implementation through other CLIs is not part of this; the bridge recipe already covers workers. [paraphrase]
- No removal or redesign of `review.backend` here. [paraphrase]
- No sandboxing of the command by flowctl. [inferred]

## Decision Context

A generic seam was chosen over another fixed backend because each vendor CLI brings its own flags, permissions and session handling to follow, and the list keeps changing. The shape copies the merge-verdict command and the review execution URL, which users and tests already know. Putting Gemini rungs back into the copilot and cursor ladders is the smaller change but only helps people who hold one of those subscriptions.

It also gives an organisation that has its own review a way to run it under flow-next's rounds and receipts, which #619 asked for.

## Parked unknowns

- Whether a panel of three draws should call the command three times concurrently or leave draw count to the wrapper; resolved by reading how the runner dispatches the existing CLI backends.

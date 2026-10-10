# Host implementation reviews use the project's standing review focus

## Goal & Context

Since 8.5.0, a review focus the project's instructions state ("reviews focus on over-engineering and YAGNI") reaches every reviewer on the codex, claude, copilot and cursor backends: when the request names no focus, the impl-review skill passes the standing one with `--focus`, for the first round and, under `--deep` or `--validate`, through the same CLI workflow. [paraphrase]

The host backend misses it. Its workflow renders each reviewer's prompt with only the focus named in the request, so a host review started by work or `flow --auto`, which never names one, runs without the project's focus, and its receipt records none. The docs (Impl Review, the review workflow guide, the model-routing policy example and the 8.5.0 changelog) say every reviewer gets the focus and the receipt records it. [paraphrase]

The fix is to give the host workflow the same fallback the CLI workflow has, so the host prompts render the standing focus and the host receipt records it. [paraphrase]

<!-- Source: 0% user / 85% [paraphrase] / 15% [inferred] -->

## Architecture & Data Models

- **The focus stays caller input, owned by the review run.** The agent running the review decides it: the focus named in the request, else the one the project's instructions state. It is rendered into each reviewer's prompt and recorded on that round's receipt, exactly as on the CLI backends. [paraphrase]
- **Re-review needs no change.** The prompt builder already carries the prior receipt's focus into a re-review when the caller passes none, so a host re-review keeps the focus its first round recorded. [inferred]

## Acceptance Criteria

- **R1:** A host implementation review whose request names no focus renders the review focus the project's instructions state into every reviewer prompt of the round: each panel draw and the one-reviewer round. Errors: when the instructions state no focus, the prompts carry none and render as they do today. [paraphrase]
- **R2:** The host review receipt records the focus the round's prompts carried, including a standing focus from R1, and records none when they carried none. No error surface beyond R1. [paraphrase]
- **R3:** On the host backend a focus named in the request replaces the standing one for that review, matching the CLI backends. No error surface beyond R1. [paraphrase]
- **R4:** The CLI backends' focus handling is unchanged, including under `--deep` and `--validate`. No error surface beyond R1. [inferred]
- **R5:** It is guidance to the agent running the review, worded like the CLI workflow's fallback; no check enforces it (G4). [inferred]

## Boundaries

- No flowctl change; the prompt builder and receipt handling already take a focus. [inferred]
- The fixed "Focus areas" lists inside the deep-pass prompt templates (security, performance) are unrelated and stay as they are. [inferred]
- Plan review and completion review are out of scope. [inferred]
- No new config key; the project's instruction file stays where the standing focus is stated. [paraphrase]

## Decision Context

The 8.5.0 docs claim the standing focus reaches every reviewer and the receipt records it; that is true on the CLI backends and false on the host backend. Making the code match the docs was chosen over narrowing the docs, because the host backend is setup's recommended default on Cursor and the reason for the feature (a project's focus reaching reviewers that do not read its instruction file) applies to host reviewers too. Ships as patch release 8.5.1. [paraphrase]

## Strategy Alignment

- "Agent first": the agent reads the project's stated focus and passes it; flow-next records what was passed. No form, field or check is added. [paraphrase]

## Strategy Conflicts

None found.

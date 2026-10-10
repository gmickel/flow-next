# Task-scoped implementation reviews carry a review focus

## Goal & Context

A project that states a review focus (for example, an instruction file saying reviews should look for over-engineering, slop and YAGNI) cannot get that focus to the reviewers of a task. Every review a task build runs is task-scoped, and the focus never arrives. [paraphrase]

Today the three impl-review routes disagree:

- The fan-out route refuses `--focus` when the review names a task, so that a focus the reviewers never saw is not stamped on the receipt (the PR #392 review). [paraphrase]
- The single-reviewer backend route accepts `--focus` on a task review, leaves it out of the task prompt, and still writes it to the receipt: the exact false record the fan-out refusal exists to prevent. [inferred]
- The host route's rendered prompt drops the focus for a task review without saying so. [inferred]

There is no other channel. The project config has no review-guidance key, and Codex reviewers deliberately run without the repo's AGENTS.md, because a reviewer that read it adopted the coordinator role and ended without a verdict (#331). `.flow/criteria.md` reaches completion review, and impl review only for a one-task spec. [paraphrase]

The fix is to let the existing flag through: a task review given a focus shows it to every reviewer and records it on the receipt, and the impl-review skill tells the agent running the review to pass the focus the project's instructions state. [paraphrase]

<!-- Source: 0% user / 75% [paraphrase] / 25% [inferred] -->

## Architecture & Data Models

- **The focus is caller input, owned by the review run.** It is supplied per review invocation, rendered into each reviewer's prompt, and recorded on that review's receipt. It is not stored in config, the task spec, or the spec. [paraphrase]
- **The receipt's focus field keeps its meaning:** the focus the reviewers of that round saw. Re-review rounds keep adopting the prior receipt's focus when the caller passes none, as standalone reviews already do. [inferred]
- **The task prompt gains the same focus section the standalone prompt already has**, present only when a focus is given. [inferred]

## Acceptance Criteria

- **R1:** A task-scoped implementation review given `--focus` shows that focus to every reviewer it dispatches: the single reviewer on every backend, each fan-out draw, and the prompt rendered for the host reviewer. Errors: an empty or whitespace-only focus is treated as no focus. [paraphrase]
- **R2:** A review receipt records a focus only when that review's reviewers received it, on every backend and route. A task review run with a focus records it; a review whose prompt carried no focus records none. No error surface beyond R1. [paraphrase]
- **R3:** A re-review round of a task review uses the prior receipt's focus when the caller passes none, so a resumed reviewer keeps the requested focus. Errors: an unreadable or malformed prior receipt means no carried focus, as for standalone reviews today. [inferred]
- **R4:** A task review without a focus renders the same prompt it renders today, with no empty focus section. Standalone reviews are unchanged. No error surface beyond R1. [inferred]
- **R5:** The implementation-review skill tells the agent running a review to pass, with `--focus`, a review focus the project's instructions state, for task and standalone reviews alike. It is guidance; no check enforces it (G4). [paraphrase]

## Boundaries

- No new config key for review guidance; the project's instruction file stays the place where the focus is stated. [paraphrase]
- `.flow/criteria.md` handling is unchanged; standing criteria on the default route belong to fn-279. [inferred]
- Codex reviewers keep running without the repo's AGENTS.md. [inferred]
- Plan review and completion review are out of scope. [inferred]
- No claim that a focus improves review quality; the always-on smell baseline already names speculative generality and pass-through layers, and the effect is unmeasured. [paraphrase]

## Decision Context

The paste that raised this offered two fixes: "a per-project review focus in flow-next config, added to every review prompt; or writing the YAGNI focus into each task spec, which is clumsy." Passing the existing flag through was chosen over both. A config key would be a second home for guidance the project's instruction file already holds, and it adds structure the agent must satisfy (G4). Writing the focus into each task spec is clumsy, and it stays local to each spec. Sending `.flow/criteria.md` to every task review was also rejected: criteria are judged once per spec at completion, and per-task judgments would mostly come back n/a. [paraphrase]

The PR #392 refusal protected receipt truth, not a design preference against a focus on task reviews. Once task reviewers receive the focus, recording it is truthful, so the refusal is no longer needed. The single-reviewer route's current behaviour (record without showing) breaks the same rule and is fixed here. [inferred]

## Strategy Alignment

- "Agent first": the agent reads the project's stated focus and passes it; flow-next records what was passed. No form, field or check is added. [paraphrase]

## Strategy Conflicts

None found.

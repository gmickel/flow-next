# Prototype before ask (routing reference 5 of 6)

**Decision record**

- Source: the maintainer's observation that the most common unnecessary plain-text numbered prompt asks the user to predict something the agent could run.
- Trigger: flow or a routed skill is about to ask a "which approach" or "what should this do" question.
- Purpose: replace a class of questions with an experiment; keep the questions that only a person can answer.
- Evidence: a fork whose answer is observable (behaviour, output, timing, layout) is settled faster and more reliably by running something than by asking someone to guess.
- Disposition: keep. Cheap to state, cheap to follow.

## Classify the fork first

Before asking, name what the answer depends on:

| The answer is | Settle it by | Example |
|---|---|---|
| Observable: behaviour, output, timing, layout, a failing case, a measurement | A prototype, a spike, a test, or a measurement; then continue with the observed answer and say what was run | "Does the parser accept the legacy header?" - run it. "Is the query fast enough?" - time it. "Does the layout hold at 400px?" - render it |
| A product or preference call no experiment can settle: scope, priority, authority, taste, a business rule | One plain-text numbered prompt, with the observed facts already in hand | "Should deleted rows stay visible to admins?" "Which of the two names?" |

## Rules

- An observable fork is never a question. Run the smallest experiment that discriminates the branches, record what ran, and continue.
- A product or preference fork becomes at most one plain-text numbered prompt, asked with `plain-text numbered prompt` (plain-text numbered fallback on hosts without it), only when the two routes would materially differ.
- Under any autonomy marker a product or preference fork stops with `NEEDS_HUMAN` and the observed facts; a prototype still runs when it is cheap and reversible.
- A prototype is evidence, never a deliverable: it is discarded or folded into the routed stage's work, and its result is named in the report.

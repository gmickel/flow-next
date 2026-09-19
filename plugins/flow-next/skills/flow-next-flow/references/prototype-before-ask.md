# Prototype before ask (routing reference 5 of 6)

**Decision record**

- Source: the maintainer's observation that the most common unnecessary blocking question asks the user to predict something the agent could run.
- Trigger: flow or a routed skill is about to ask a "which approach" or "what should this do" question.
- Purpose: replace a class of questions with an experiment; keep the questions that only a person can answer.
- Evidence: a fork whose answer is observable (behaviour, output, timing, layout) is settled faster and more reliably by running something than by asking someone to guess.
- Disposition: keep. Cheap to state, cheap to follow.

## Classify the fork first

First use this hop's `fork_present` and `fork_kind` answers from route, or call `$FLOWCTL judge --preset fork-gate --state-file <fork-state.json> --json` with the proposed fork in `text`. Apply the preset decision before inventing alternatives: fork-present < 0.5 means no fork and no question, reported as `fork-gate: none (jev <p>)`. At >= 0.5, `observable` or `product_or_preference` at confidence >= 0.5 follows the table below and prints `fork-gate: observable (jev <confidence>)` or `fork-gate: preference (jev <confidence>)`. A below-floor classification or `none_of_the_above` at any confidence uses today's judgment and prints `fork-gate: host (jev below floor)`; unavailable prints `fork-gate: host (jev-unavailable(<reason>))` and uses the same fallback. The autonomy and one-question rules below remain binding.

On fallback, name what the answer depends on:

| The answer is | Settle it by | Example |
|---|---|---|
| Observable: behaviour, output, timing, layout, a failing case, a measurement | A prototype, a spike, a test, or a measurement; then continue with the observed answer and say what was run | "Does the parser accept the legacy header?" - run it. "Is the query fast enough?" - time it. "Does the layout hold at 400px?" - render it |
| A product or preference call no experiment can settle: scope, priority, authority, taste, a business rule | One blocking question, with the observed facts already in hand | "Should deleted rows stay visible to admins?" "Which of the two names?" |

Apply the standalone result or shared route subdecision before the table's action:

```python
# fence:judge-fork-consumer
if not result["available"]:
    fork_action = "host"
    fork_line = "fork-gate: host (jev-unavailable(%s))" % result["reason"]
else:
    decision = result["decision"].get("fork", result["decision"])
    fork_action = decision["value"]
    if fork_action == "host":
        fork_line = "fork-gate: host (jev below floor)"
    else:
        probability = (result["answers"]["fork_present"]["noul"] if fork_action == "none"
                       else result["answers"]["fork_kind"]["confidence"])
        label = "preference" if fork_action == "product_or_preference" else fork_action
        fork_line = "fork-gate: %s (jev %.2f)" % (label, probability)
```

`none` continues without a question; `observable` runs the experiment; `product_or_preference` follows the question/autonomy rules; `host` uses the original table judgment. Print `fork_line` in the hop report.

## Rules

- An observable fork is never a question. Run the smallest experiment that discriminates the branches, record what ran, and continue.
- A product or preference fork becomes at most one blocking question, asked with `AskUserQuestion` (plain-text numbered fallback on hosts without it), only when the two routes would materially differ.
- Under any autonomy marker a product or preference fork stops with `NEEDS_HUMAN` and the observed facts; a prototype still runs when it is cheap and reversible.
- A prototype is evidence, never a deliverable: it is discarded or folded into the routed stage's work, and its result is named in the report.

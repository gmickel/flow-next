# Review model registry for GPT-6.2 and Fable 5.2, Fable only when pinned

## Goal & Context

OpenAI and Anthropic released new models. The Codex CLI serves GPT-6.2 Sol and GPT-6.2 Astra and labels GPT-6.1 Sol, flow-next's current Codex review default, as the previous generation. Copilot lists GPT-6.2 Sol, GPT-6.2 Astra and Claude Fable 5.2 as generally available. Claude Code serves `claude-fable-5-2`. flow-next's review rankings know none of these, so a team without a model pin keeps getting the older models, and a team that pins a new one gets a warning for an unknown model.

The rankings also decide cost for people who never chose a model. A bare backend name (`claude`, `codex`, `copilot`), which is what setup stores by default, runs every review on the top of that backend's ranking. The top of the Claude ranking is Fable, the most expensive Claude model, so a team that picks the Claude CLI reviewer for a cross-family review runs every review on Fable without ever naming it. Fable should be what a team asks for, and the documentation should make asking easy.

The users are teams choosing a review backend in setup, and teams that pin a reviewer model.

<!-- Source: 40% user / 30% [paraphrase] / 30% [inferred] -->

## Architecture & Data Models

**Automatic choice versus a pin.** Each backend's ranking is what flowctl picks from when the backend spec names no model: the top runs first, and the fallback steps down the list on that backend's model-unavailable signature. A model named in the spec bypasses the ranking. This spec keeps that split and adds one rule: Fable models are never chosen automatically on any backend. They are not the top of a ranking and the fallback never steps onto them. Pinned, they run as named, with no unknown-model warning.

**The tops.**

| Backend | Top when nothing is pinned | Fable |
|---|---|---|
| claude | `claude-opus-5-5` at high | `claude-fable-5-2`, `claude-fable-5-1` pinned only |
| copilot | Settled by the reviewer study below, among GPT-6.2 Astra, GPT-6.2 Sol and GPT-6 Astra | `claude-fable-5.2`, `claude-fable-5.1` pinned only |
| codex | Settled by the reviewer study below, among GPT-6.2 Astra, GPT-6.2 Sol and GPT-6.1 Sol | not served |
| cursor | unchanged | not in the ranking today; stays out |

`gpt-6.2-astra` and `gpt-6.2-sol` join the Codex and Copilot rankings in the order the study sets. The invariant that a backend's default equals the top of its ranking still holds.

**Codex host agents.** The Codex mirror pins its generated agents to a baseline model, and those baselines follow the same study (the reviewer baseline) and the scout screen (the scout baselines).

**Signatures.** The fallback steps down only on each CLI's own model-unavailable text, and two of the stored markers no longer match what the CLIs print (observed 2026-11-18):

- Copilot 1.0.114, unknown model: `Execution failed: Model "<id>" is not available.` The stored marker is `from --model flag is not available`.
- Codex 0.169.1 and 0.170.0 signed in with a ChatGPT account, model the account cannot use: `ERROR: The '<id>' model is not supported when using Codex with a ChatGPT account.` The stored markers are `requires a newer version of Codex` and `model_not_found`.

Codex 0.169.1 already serves `gpt-6.2-sol` and `gpt-6.2-astra`, so the CLI version is not the near risk; the account text is.

<!-- Source: 25% user / 25% [paraphrase] / 50% [inferred] -->

## API Contracts

No new command, flag or config key. The documented way to use Fable:

```text
flowctl config set review.backend claude:claude-fable-5-2:high
flowctl config set review.backend copilot:claude-fable-5.2
```

For host reviews, the reviewer line of the project's model-routing block names Fable.

<!-- Source: 30% user / 20% [paraphrase] / 50% [inferred] -->

## Edge Cases & Constraints

- **Existing pins keep working.** A spec that names `claude-fable-5-1`, `gpt-6.1-sol` or any other model runs that model, as today.
- **Bare `claude` changes model.** A team on a bare `claude` reviewer moves from Fable 5.1 to Opus 5.5 at the next review. The changelog says so, with the one-line pin that restores Fable.
- **A CLI too old for the new top.** The fallback steps down to the next ranked model on that CLI's unavailable signature, never onto Fable.
- **Copilot quota and org policy.** A Copilot answer that is a quota or policy refusal is not an unavailable model and does not step down.

## Acceptance Criteria

- **R1:** With a bare `claude` review backend, a review runs `claude-opus-5-5` at high. Errors: when Opus 5.5 is unavailable on the installed CLI, the fallback steps down the non-Fable ranking. [paraphrase]
- **R2:** No backend's automatic choice or fallback selects a Fable model. No error surface. [paraphrase]
- **R3:** A pinned `claude:claude-fable-5-2`, `claude:claude-fable-5-1`, `copilot:claude-fable-5.2` or `copilot:claude-fable-5.1` runs that model and prints no unknown-model warning. No error surface beyond the CLI's own. [paraphrase]
- **R4:** The Codex and Copilot rankings contain `gpt-6.2-astra` and `gpt-6.2-sol`, and their tops are the ones the reviewer study selects under its pre-registered rule. No error surface. [inferred]
- **R5:** The Codex mirror's reviewer and scout baselines are the models the study and the scout screen select, and the generated agents carry them. No error surface. [inferred]
- **R6:** The Copilot fallback steps down on Copilot's current unavailable text, and the Codex fallback steps down on the ChatGPT-account text, while neither steps down on a quota or authentication failure (Copilot's quota text is `You have exceeded your monthly quota`). Errors: a failure that matches no signature propagates unchanged, as today. [inferred]
- **R7:** The documentation that names rankings or defaults (the flowctl reference, the per-host reach pages, the setup review question, the changelog) states the new tops with the date they were observed, says Fable is chosen only when pinned, and shows how to pin it. No error surface. [paraphrase]

Tests that pin defaults are updated to the new tops, and new cases cover R2, R3 and both signatures (G2). Docs and the flow-next.dev pages that describe review backends change in the same release.

## Boundaries

- No change to the Cursor ranking beyond what the study shows is needed. [inferred]
- No new config key or flag for choosing Fable. A pin is the mechanism. [paraphrase]
- No change to how host reviews pick a model. [inferred]
- No price table in the product. Cost is named in the docs only as "the most expensive Claude tier". [inferred]

## Decision Context

The maintainer decided on 2026-11-18 that the top of the Claude ranking, the model a team gets without choosing one, is not Fable, and that the documentation shows clearly how to use Fable. Keeping Fable out of the fallback as well follows from the same reasoning: a step down that lands on the most expensive tier is a choice nobody made.

The Codex and Copilot tops are not decided here. GPT-6.1 Sol missed defects in this month's reviews that later passes found, and a reviewer study replays those reviewed commits on GPT-6.1 Sol, GPT-6.2 Sol and GPT-6.2 Astra with a pre-registered rule (`~/work/agent-evals/studies/reviewer-model-2026-11/`). Its result fills R4 and R5.

<!-- Source: 30% user / 10% [paraphrase] / 60% [inferred] -->

## Parked unknowns

- The Codex and Copilot tops and the Codex mirror baselines: resolved by the reviewer study and the scout screen.

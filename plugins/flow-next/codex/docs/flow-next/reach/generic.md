# Reach: generic fallback

The page an **undetectable harness** resolves to. If you are reading this because the harness could not be identified, say so once and proceed on the assumptions below — a guessed harness is worse than a named fallback.

How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Assume yes** — something is executing this, and that something is the default executor for every unset tier. |
| In-host subagent | **Assume no** until observed working. |
| Shell out to another CLI | **Assume no** until observed working. |

## What is unavailable

Unknown, which is treated as unavailable. Absence of evidence is the right default here precisely because the cost of assuming reach and being wrong is a silent, unrouted run.

## Degradation

Every tier runs on the session model, and the degradation is stated once. That is the shipped default: with no reach at all, the pipeline still runs end to end and only the tier split is lost.

## Discover, then invoke

Before concluding a mechanism is missing, try the cheapest discovery available: ask the harness what it offers, ask any CLI on the machine for its own models. One command turns an assumption into a fact — and if the harness turns out to be a supported one, use its page in [`README.md`](README.md) instead of this one.

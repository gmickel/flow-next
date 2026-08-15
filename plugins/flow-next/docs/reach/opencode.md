# Reach: OpenCode (community port)

How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

flow-next reaches this harness through a **community port**, so the reach surface is whatever that port exposes at the version you installed — this page states the floor, not a promise.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Port-dependent** — assume unavailable until a fan-out is observed working. |
| Shell out to another CLI | **Port-dependent** — available wherever the port lets the agent run shell commands, which is the usual case. |

## What is unavailable

Anything the port has not implemented. Treat both dispatch mechanisms as unconfirmed rather than absent, and confirm by trying once.

## Degradation

Every unconfirmed mechanism degrades to the session model, stated once. That is the shipped default, so a port with no dispatch mechanisms still runs the whole pipeline — only the tier split is lost.

## Discover, then invoke

Ask the port what it offers, and ask each installed CLI for its own models, at the moment of use. Where the port's behavior differs from what this page assumes, the port's behavior is the truth.

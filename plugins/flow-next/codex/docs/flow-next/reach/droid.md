# Reach: Factory Droid

> **Codex install note:** commands written as `/flow-next:<name>` in this page are invoked on this host as `$flow-next-<name>` (or picked from the skills dropdown); examples prefixed `claude -p` or `/loop` are Claude Code host examples and run there unchanged.


How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes** — the harness reads flow-next's agent definitions directly. Subagent behavior differs from the canonical host in ways that are not routing (dispatch semantics, timing), so verify a fan-out once rather than assuming parity. |
| Shell out to another CLI | **Yes** — the harness runs shell commands, so any installed, authenticated CLI is reachable. |

## What is unavailable

Nothing structural for routing. The known divergences here are tool and hook naming, which flow-next already absorbs elsewhere and which do not change how a model is reached.

## Degradation

A tier this harness cannot honor runs on the session model and says so once. If a subagent dispatch behaves differently than expected, the work still completes in session — reach degrades, it does not fail.

## Discover, then invoke

Ask the harness and each installed CLI what they currently offer, at the moment of use. A stored answer is the thing that goes stale.

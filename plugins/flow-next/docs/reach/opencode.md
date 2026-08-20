# Reach: OpenCode

How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

flow-next reaches this harness through the in-repo installer (`scripts/install-opencode.sh` — canonical skills plus generated agents/commands scattered into `~/.config/opencode/`). The reach surface below is what OpenCode itself exposes; the flowctl-resolution claim is gated on the live verification recorded in [`../platforms.md`](../platforms.md#opencode).

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes (schema-level)** — OpenCode dispatches markdown subagents via its Task tool; the installer generates flow-next's agents into `agents/`. Confirm a fan-out once per OpenCode major before relying on it. |
| Shell out to another CLI | **Yes** — bash is a first-class OpenCode tool; the standard bridge recipes apply. |

## What is unavailable

A native blocking-ask primitive (numbered-prompt fallback applies) and any agent `model:` tier honoring — generated agents inherit the session model. Ralph is not supported.

## Degradation

Every unconfirmed mechanism degrades to the session model, stated once. That is the shipped default, so a port with no dispatch mechanisms still runs the whole pipeline — only the tier split is lost.

## Discover, then invoke

Ask the harness what it offers, and ask each installed CLI for its own models, at the moment of use. Where OpenCode's behavior differs from what this page assumes, OpenCode's behavior is the truth.

# Reach: Cursor

> **Codex install note:** commands written as `/flow-next:<name>` in this page are invoked on this host as `$flow-next-<name>` (or picked from the skills dropdown); examples prefixed `claude -p` or `/loop` are Claude Code host examples and run there unchanged.


How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes, but an agent definition's model field is ignored** — subagents inherit the session model. The escape hatch is caller-side: name the model in the dispatch itself, and the harness honors it (it also self-corrects a near-miss identifier). There is no mechanism that rewrites an agent definition's model into this harness's own naming, and none is planned. |
| Shell out to another CLI | **Yes** — the harness runs shell commands, so any installed, authenticated CLI is reachable, including this harness's own. |

## What is unavailable

Model selection carried by an agent definition. Every other reach mechanism is present.

## Degradation

With no caller-side model in the dispatch, every tier resolves to the session model — which is exactly the shipped default and needs no configuration. When a tier matters here (a reviewer from a family that did not write the diff, most often), name the model in the dispatch or shell out; otherwise let it degrade and say so once.

## Discover, then invoke

This harness's CLI lists the models it can reach, and that list moves — ask it immediately before pinning one in a dispatch rather than copying an identifier from a document.

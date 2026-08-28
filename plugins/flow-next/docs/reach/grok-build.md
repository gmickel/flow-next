# Reach: Grok Build

How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes** - flow-next's agent definitions dispatch here, verified by a full planning fan-out. Every model it can reach natively belongs to one family. |
| Shell out to another CLI | **Yes** - the harness runs shell commands, so another vendor's CLI is how a different family is reached from here. |

## What is unavailable

A second model family in-host. That matters for exactly one tier: **reviewer**, whose whole point is a verdict from outside the writer's family. Nothing native satisfies it when the writer is this harness's own family.

## Degradation

When the reviewer tier cannot be satisfied natively, the honest outcomes are: shell out to another vendor's CLI, or state that the review is same-family and let a human decide. An attended session asks; an unattended one stops and says a human is needed. A same-family verdict presented as an independent one is the failure this page exists to prevent.

## Discover, then invoke

Ask the harness and any installed CLI what they currently offer before naming a model. What is reachable from this machine and this account is a property of the machine, not of a document.

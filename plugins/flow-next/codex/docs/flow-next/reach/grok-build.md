# Reach: Grok Build

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


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

## Models observed (2026-09-05)

The `claude` review backend (`review.backend claude`, observed 2026-09-05) is one way to satisfy the reviewer tier from here: it shells out to `claude -p` (read-only, prompt on stdin) and steps the ranking `claude-fable-5-1` → `claude-opus-5` → `claude-sonnet-5` → `claude-haiku-4-5` (ids probed 2026-09-05 on Claude Code 2.1.260; the CLI lists no models, so the ladder steps that static ranking only), a second family with the same receipt, ladder and fix loop as the `codex` / `copilot` / `cursor` backends.

## Discover, then invoke

Ask the harness and any installed CLI what they currently offer before naming a model. What is reachable from this machine and this account is a property of the machine, not of a document.

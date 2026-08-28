# Reach: Claude Code

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; it is the default executor for every unset tier. |
| In-host subagent | **Yes** - subagents are spawned in-host, and an agent definition's model field is honored, so a tier can execute on a different model without leaving the session. |
| Shell out to another CLI | **Yes** - the harness runs shell commands, so any CLI installed and authenticated on the machine is reachable, in either direction. |

## What is unavailable

Nothing structural. What can be missing is *situational*: a model your account cannot use, a CLI that is not installed or not logged in.

## Degradation

A tier naming a model this harness cannot reach falls back to the session model, says so once, and continues. No probing, no question, no failure - an unreachable name is a fact to report, not an error to prevent.

## Discover, then invoke

Ask, don't assume. The harness lists the models it can run, and each installed CLI lists its own; read that list at the moment of use rather than trusting a value stored earlier. One command beats a stored fact that goes stale.
